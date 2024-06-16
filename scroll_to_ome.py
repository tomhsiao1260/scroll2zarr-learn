import sys
import re
import shutil
import argparse
from pathlib import Path
import numpy as np
import tifffile
import zarr

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

    tzarr[0:100, 500:1000, 300:700] = 150

    data = zarr.open(zarrdir, mode="r")

    print('zarr shape: ', data.shape)
    print('min, max value: ', np.min(data), np.max(data))

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
    zarr_only = args.zarr_only
    
    slices = None
    zarr_only = True
    
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


if __name__ == '__main__':
    sys.exit(main())