"""Các tầng nghiệp vụ (xem modules/README.md).

Tầng: ``domain`` (dùng chung) ← ``data`` ← ``understanding`` ← ``solvers`` ← ``decision``.
Quy ước import:
- Mỗi package là một mặt tiền: nơi khác chỉ import từ ``datamate.modules.<tầng>.<package>``,
  danh sách công khai nằm ở ``__all__`` của ``__init__.py``.
- Bên trong cùng một package thì import thẳng từ file anh em (tránh vòng import).
- Chỉ import tầng thấp hơn; các bộ giải trong ``solvers`` không import lẫn nhau.
  Khoá bằng tests/test_layers.py.
"""
