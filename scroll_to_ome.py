import sys
import argparse

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

    args = parser.parse_args()

    print(args.input_tiff_dir, args.output_zarr_ome_dir)

if __name__ == '__main__':
    sys.exit(main())