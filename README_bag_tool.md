# bag_tool.py

扫描目录中的 `.bag` 文件并生成清单，或将清单与目标目录进行比对。

## 环境要求

Python 3.9+，无需第三方依赖。

---

## 导出模式

递归扫描指定目录，将所有 `.bag` 文件的路径、文件名、大小写入 txt 清单。

```bash
python bag_tool.py export --path <扫描目录> [--output <输出文件>]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--path` | 要扫描的目录（含子文件夹） | 必填 |
| `--output` | 输出的 txt 文件路径 | `bag_list.txt` |

**示例**

```bash
python bag_tool.py export --path /data/bags --output my_bags.txt
```

**输出格式**（制表符分隔）

```
# exported: 2026-05-09 10:00:00
# source: /data/bags
# path	filename	size_bytes
/data/bags/run1/foo.bag	foo.bag	104857600
/data/bags/run2/bar.bag	bar.bag	52428800
```

---

## 比对模式

将已有的 txt 清单与目标目录进行比对，找出缺失的 bag 和文件大小不一致的 bag。

```bash
python bag_tool.py compare --txt <清单文件> --path <比对目录> [--output <报告文件>]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--txt` | 由导出模式生成的 txt 文件 | 必填 |
| `--path` | 要比对的目录（含子文件夹） | 必填 |
| `--output` | 输出的报告文件路径 | `report.txt` |

> 比对规则：仅匹配**文件名**，不考虑目录结构差异。

**示例**

```bash
python bag_tool.py compare --txt my_bags.txt --path /backup/bags --output report.txt
```

**report.txt 结构**

```
# bag_tool compare report
# generated: 2026-05-09 10:05:00
# reference txt : /home/user/my_bags.txt
# compare path  : /backup/bags
# total in ref  : 10
# matched OK    : 8
# missing       : 1
# size mismatch : 1

============================================================
MISSING BAGS
============================================================
  foo.bag  (expected size: 100.00 MB / 104857600 B)

============================================================
SIZE MISMATCH
============================================================
  filename                                  expected            actual             delta
  ----------------------------------------  ----------------  ----------------  ----------------
  bar.bag                                      50.00 MB          48.50 MB         -1.50 MB
```

---

## 注意事项

- 若同一目录下存在**同名** bag 文件，工具会在终端打印警告，导出时全部记录，比对时取第一个匹配项。
- txt 文件中的 `size_bytes` 为原始字节数，报告中的大小为自动换算的可读格式（B / KB / MB / GB / TB）。
