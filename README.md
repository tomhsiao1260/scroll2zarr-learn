# How to run

Install the packages

```python
pip install -r requirements.txt 
```

Prepare a folder called `stack` with a series of `.tif` data in it (e.g. 00.tif, 01.tif, ... 10.tif). And then run the following script. It will generate a `scroll.zarr` data for you.

```python
python scroll_to_ome.py stack scroll.zarr
```