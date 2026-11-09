#!/usr/bin/env python3
"""Verify LF-only deployment checksums without third-party Python modules."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    root = Path(__file__).resolve().parents[1]
    checksums = root / 'SHA256SUMS.txt'
    data = checksums.read_bytes()
    if b'\r' in data:
        raise SystemExit('校验清单必须使用LF换行，请重新解压原始部署包。')
    count = 0
    for line in data.decode('utf-8').splitlines():
        expected, relative = line.split('  ', 1)
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise SystemExit('文件缺失或路径无效：' + relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('文件校验失败：' + relative)
        count += 1
    packages = {ET.parse(path).getroot().findtext('name') for path in (root / 'src').glob('*/package.xml')}
    if packages != {'heritage_hall', 'heritage_robot', 'heritage_tour'}:
        raise SystemExit('部署包中的ROS模块与预期不符。')
    print(f'部署包校验通过：{count}个文件，3个ROS模块。')


if __name__ == '__main__':
    main()
