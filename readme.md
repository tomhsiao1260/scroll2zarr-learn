# Introduction

Try to learn [scroll2zarr](https://github.com/KhartesViewer/scroll2zarr) step by step.

# Details

### tifs2zarr

根據提供的 tiff 資料，產生對應的 zarr 資料

首先，把所有 tiff 路徑存進一個叫 inttiffs 的字典，好比說，檔案 `0010.tif` 的 key 值為 10，對應的 value 為該檔案路徑，以 `PosixPath` 形式儲存。itiffs 則是一個列表，記錄了所有 key 值由小到大的排序。

