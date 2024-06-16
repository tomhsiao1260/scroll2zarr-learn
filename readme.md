# Introduction

Try to learn [scroll2zarr](https://github.com/KhartesViewer/scroll2zarr) step by step.

## Command

Prepare a folder called `stack` with a series of `.tif` data in it (e.g. 00.tif, 01.tif, ... 10.tif). And then run the following script. It will generate a `scroll.zarr` data for you.

```bash
python scroll_to_ome.py stack scroll.zarr
```

## Structure

使用 `--zarr_only` 會執行 `tifs2zarr` 函數產生 zarr 檔，結構範例如下：

```
表示 z (0 到 1), y (5 到 6), x (2 到 4)

.
└── scroll.zarr
    ├── .zarray
    ├── 0
    │   ├── 5
    │   │   ├── 2
    │   │   ├── 3
    │   │   └── 4
    │   └── 6
    │       ├── 2
    │       ├── 3
    │       └── 4
    └── 1
        ├── 5
        │   ├── 2
        │   ├── 3
        │   └── 4
        └── 6
            ├── 2
            ├── 3
            └── 4
```

沒有用 `--zarr_only` 則會產生 OME/Zarr 檔，結構範例如下：

```
假設創建 6 種 level，每上升一個 level 邊長減半，資料大小變 1/8

.
└── scroll.zarr
    ├── .zattrs
    ├── .zgroup
    ├── 0
    │   ├── .zarray
    │   └── pure zarr structure (level 0)
    ├── 1
    │   ├── .zarray
    │   └── pure zarr structure (level 1)
    ├── 2
    │   ├── .zarray
    │   └── pure zarr structure (level 2)
    ├── 3
    │   ├── .zarray
    │   └── pure zarr structure (level 3)
    ├── 4
    │   ├── .zarray
    │   └── pure zarr structure (level 4)
    └── 5
        ├── .zarray
        └── pure zarr structure (level 5)
```

## Details

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

### tifs2zarr

根據提供的 tiff 資料，產生對應的 zarr 資料和 `.zarray` 隱藏檔

首先，把所有 tiff 路徑存進一個叫 inttiffs 的字典，好比說，檔案 `0010.tif` 的 key 值為 10，對應的 value 為該檔案路徑，以 `PosixPath` 形式儲存。itiffs 則是一個列表，記錄了所有 key 值由小到大的排序。

chunk_size 是每筆方塊資料的邊長，cx, cy, cz 是所有資料堆疊後各軸的長，定義好一些參數後，再來就是開啟一個 `zarr.open` 資料準備寫入。寫入方式主要就是透過 tarr 讀取 tiff 檔，透過 buf 把一個完整的 chunk 取出來，然後一個個寫進 tzarr 這個大陣列裡

tzarr 軸依序為 z, y, x，(0, 0, 0) 對應到第一張 tif 的左上角原點座標 (cz, cy, cx) 則對應對後一張 tif 的右下角座標，檔案的巢狀格式也是按照順序由小排到大

### create_ome_dir

創建 `.zarr` 資料夾

### create_ome_headers

創建 `.zattrs` 和 `.zgroup` 資料，前者不一定需要，主要是給開發者自己加入客製化資訊的屬性檔，後者則是說明使用的是 zarr 的第二版本

### resize

會在指定的 level 上，加入新的一層，也就是邊長減半的 level，好比說輸入的 `idir` 為 `scroll.zarr/0`，那輸出的 `odir` 就是 `scroll.zarr/1`

實作上，使用了 `divp1` 計算減半後的各種參數數值，以及 `skimage.transform` 把原始資料做裁切縮放

### first_new_level

使用 `--first_new_level n`，表示會用 level n-1 的資料作為基礎，往上建立其他層的 OME/Zarr 資料



