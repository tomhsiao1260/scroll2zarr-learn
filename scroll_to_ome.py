import sys
import re
import json
import shutil
import argparse
import copy
from pathlib import Path
import numpy as np
import tifffile
import zarr

# return None if succeeds, err string if fails
def create_ome_dir(zarrdir):
    # complain if directory already exists
    if zarrdir.exists():
        err = "Directory %s already exists"%zarrdir
        print(err)
        return

    try:
        zarrdir.mkdir()
    except Exception as e:
        err = "Error while creating %s: %s"%(zarrdir, e)
        print(err)
        return err

def create_ome_headers(zarrdir, nlevels):
    zattrs_dict = {
        "multiscales": [
            {
                "axes": [
                    {
                        "name": "z",
                        "type": "space"
                    },
                    {
                        "name": "y",
                        "type": "space"
                    },
                    {
                        "name": "x",
                        "type": "space"
                    }
                ],
                "datasets": [],
                "name": "/",
                "version": "0.4"
            }
        ]
    }

    dataset_dict = {
        "coordinateTransformations": [
            {
                "scale": [
                ],
                "type": "scale"
            }
        ],
        "path": ""
    }
    
    zgroup_dict = { "zarr_format": 2 }

    datasets = []
    for l in range(nlevels):
        ds = copy.deepcopy(dataset_dict)
        ds["path"] = "%d"%l
        scale = 2.**l
        ds["coordinateTransformations"][0]["scale"] = [scale]*3
        # print(json.dumps(ds, indent=4))
        datasets.append(ds)
    zad = copy.deepcopy(zattrs_dict)
    zad["multiscales"][0]["datasets"] = datasets
    json.dump(zgroup_dict, (zarrdir / ".zgroup").open("w"), indent=4)
    json.dump(zad, (zarrdir / ".zattrs").open("w"), indent=4)

def tifs2zarr(tiffdir, zarrdir, chunk_size):
    # Note this is a generator, not a list
    tiffs = tiffdir.glob("*.tif")
    rec = re.compile(r'([0-9]+)\.\w+$')
    # rec = re.compile(r'[0-9]+$')
    inttiffs = {}
    for tiff in tiffs:
        tname = tiff.name
        match = rec.match(tname)
        if match is None:
            continue
        # Look for last match (closest to end of file name)
        # ds = match[-1]
        ds = match.group(1)
        itiff = int(ds)
        if itiff in inttiffs:
            err = "File %s: tiff id %d already used"%(tname,itiff)
            print(err)
            return err
        inttiffs[itiff] = tiff
    if len(inttiffs) == 0:
        err = "No tiffs found"
        print(err)
        return err

    itiffs = list(inttiffs.keys())
    itiffs.sort()
    z0 = 0

    print('tiff list 0~9: ', itiffs[:10])
    
    # for testing
    # itiffs = itiffs[2048:2048+256]
    
    minz = itiffs[0]
    maxz = itiffs[-1]
    cz = maxz-z0+1
    
    tiff0 = tifffile.imread(inttiffs[minz])
    ny0, nx0 = tiff0.shape
    dt0 = tiff0.dtype
    print("tiff size", nx0, ny0, "z range", minz, maxz)

    cx = nx0
    cy = ny0
    x0 = 0
    y0 = 0
    print("cx,cy,cz",cx,cy,cz)
    print("x0,y0,z0",x0,y0,z0)

    store = zarr.NestedDirectoryStore(zarrdir)
    tzarr = zarr.open(
            store=store, 
            shape=(cz, cy, cx), 
            chunks=(chunk_size, chunk_size, chunk_size),
            dtype = tiff0.dtype,
            write_empty_chunks=False,
            fill_value=0,
            compressor=None,
            mode='w', 
            )

    # nb of chunks in y direction that fit inside of max_gb
    chy = cy // chunk_size + 1

    # nb of y chunk groups
    ncgy = cy // (chunk_size*chy) + 1
    print("chy, ncgy", chy, ncgy)
    buf = np.zeros((chunk_size, min(cy, chy*chunk_size), cx), dtype=dt0)
    for icy in range(ncgy):
        ys = icy*chy*chunk_size
        ye = ys+chy*chunk_size
        ye = min(ye, cy)
        if ye == ys:
            break
        prev_zc = -1
        for itiff in itiffs:
            z = itiff-z0
            tiffname = inttiffs[itiff]
            print("reading",itiff,"     ", end='\r')
            # print("reading",itiff)
            tarr = tifffile.imread(tiffname)
            # print("done reading",itiff, end='\r')
            # tzarr[itiff,:,:] = tarr
            ny, nx = tarr.shape
            if nx != nx0 or ny != ny0:
                print("\nFile %s is the wrong shape (%d, %d); expected %d, %d"%(tiffname,nx,ny,nx0,ny0))
                continue
            cur_zc = z // chunk_size
            if cur_zc != prev_zc:
                if prev_zc >= 0:
                    zs = prev_zc*chunk_size
                    ze = zs+chunk_size
                    if ncgy == 1:
                        print("\nwriting, z range %d,%d"%(zs+z0, ze+z0))
                    else:
                        print("\nwriting, z range %d,%d  y range %d,%d"%(zs+z0, ze+z0, ys+y0, ye+y0))
                    tzarr[zs:z,ys:ye,:] = buf[:ze-zs,:ye-ys,:]
                    buf[:,:,:] = 0
                prev_zc = cur_zc
            cur_bufz = z-cur_zc*chunk_size
            # print("cur_bufzk,ye,ys", cur_bufz,ye,ys)
            buf[cur_bufz,:ye-ys,:] = tarr[ys:ye,:]

        if prev_zc >= 0:
            zs = prev_zc*chunk_size
            ze = zs+chunk_size
            ze = min(itiffs[-1]+1-z0, ze)
            if ze > zs:
                if ncgy == 1:
                    print("\nwriting, z range %d,%d"%(zs+z0, ze+z0))
                else:
                    print("\nwriting, z range %d,%d  y range %d,%d"%(zs+z0, ze+z0, ys+y0, ye+y0))
                # print("\nwriting (end)", zs, ze)
                # tzarr[zs:zs+bufnz,:,:] = buf[0:(1+cur_bufz)]
                tzarr[zs:ze,ys:ye,:] = buf[:ze-zs,:ye-ys,:]
            else:
                print("\n(end)")
        buf[:,:,:] = 0

def resize(zarrdir, old_level, algorithm="mean"):
    idir = zarrdir / ("%d"%old_level)
    if not idir.exists():
        err = "input directory %s does not exist" % idir
        print(err)
        return(err)
    odir = zarrdir / ("%d"%(old_level+1))
    print(zarrdir, idir, odir)
    
    idata = zarr.open(idir, mode="r")
    
    # print(idata.chunks, idata.shape)
    print("Creating level", old_level+1,"  input array shape", idata.shape)

def main():
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="Create OME/Zarr data store from a set of TIFF files")
    parser.add_argument(
            "input_tiff_dir", 
            help="Directory containing tiff files")
    parser.add_argument(
            "output_zarr_ome_dir", 
            help="Name of directory that will contain OME/zarr datastore")
    parser.add_argument(
            "--chunk_size", 
            type=int, 
            default=128, 
            help="Size of chunk")
    parser.add_argument(
            "--nlevels", 
            type=int, 
            default=6, 
            help="Number of subdivision levels to create, including level 0")
    parser.add_argument(
            "--zarr_only", 
            action="store_true", 
            help="Create a simple Zarr data store instead of an OME/Zarr hierarchy")

    args = parser.parse_args()

    zarrdir = Path(args.output_zarr_ome_dir)
    if zarrdir.suffix != ".zarr":
        print("Name of ouput zarr directory must end with '.zarr'")
        return 1

    tiffdir = Path(args.input_tiff_dir)
    if not tiffdir.exists():
        print("Input TIFF directory",tiffdir,"does not exist")
        return 1

    chunk_size = args.chunk_size
    nlevels = args.nlevels
    zarr_only = args.zarr_only
    algorithm = 'mean'
    
    if zarr_only:
        if zarrdir.exists():
            print("removing", zarrdir)
            shutil.rmtree(zarrdir)

    if zarr_only:
        err = tifs2zarr(tiffdir, zarrdir, chunk_size)
        if err is not None:
            print("error returned:", err)
            return 1
        return

    err = create_ome_dir(zarrdir)
    if err is not None:
        print("error returned:", err)
        return 1
    
    err = create_ome_headers(zarrdir, nlevels)
    if err is not None:
        print("error returned:", err)
        return 1

    print("Creating level 0")
    err = tifs2zarr(tiffdir, zarrdir/"0", chunk_size)
    if err is not None:
        print("error returned:", err)
        return 1

    old_level = 0
    err = resize(zarrdir, old_level, algorithm)


if __name__ == '__main__':
    sys.exit(main())