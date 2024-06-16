# Introduction

Try to learn [scroll2zarr](https://github.com/KhartesViewer/scroll2zarr) step by step.

# Details

### tifs2zarr

根據提供的 tiff 資料，產生對應的 zarr 資料

首先，把所有 tiff 路徑存進一個叫 inttiffs 的字典，好比說，檔案 `0010.tif` 的 key 值為 10，對應的 value 為該檔案路徑，以 `PosixPath` 形式儲存。itiffs 則是一個列表，記錄了所有 key 值由小到大的排序。

chunk_size 是每筆方塊資料的邊長，cx, cy, cz 是所有資料堆疊後各軸的長

### zarr

zarr 產生的核心程式碼如下：

```python
store = zarr.NestedDirectoryStore('scroll.zarr')

tzarr = zarr.open(
    store=store, 
    shape=(cz, cy, cx), 
    chunks=(128, 128, 128),
    dtype = 'uint16',
    write_empty_chunks=False,
    fill_value=0,
    compressor=None,
    mode='w',
    )

tzarr[0:100, 500:1000, 300:700] = 150
```

首先是定義一個 store，這裡用 `zarr.NestedDirectoryStore` 巢狀的方式儲存。然後 `zarr.open` 創建這樣的結構，這會回傳一個陣列，大小為 shape。這時候只要對陣列寫入資料，就會自動生成對應的 zarr 檔案

因為上面例子 `write_empty_chunks` 為 False，所以只會產生下面資料： `./scroll.zarr/0/3-6/2-5`。這是因為 chunk 邊長為 128，cz 軸從 0 到 100，所以 z 軸第 0 個需寫入，cy 軸從 500 到 1000，所以 y 軸第 3 到 6 個需寫入，cx 軸從 300 到 700，所以 x 軸第 2 到 5 個需寫入。另外也可以開啟 `./scroll.zarr/.zarray` 隱藏檔，這記錄了資料的相關配置資訊

另外，也可以用下面語法讀取 zarr 檔案：

```python
data = zarr.open('scroll.zarr', mode="r")

print('zarr shape: ', data.shape)
print('min, max value: ', np.min(data), np.max(data))
```



