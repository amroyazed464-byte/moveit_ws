#!/usr/bin/env python3
"""Export the committed three-package project, without development artifacts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('heritage_hall', 'heritage_robot', 'heritage_tour')
TOOLS = {'install_dependencies.sh', 'build.sh', 'start_demo.sh', 'verify_package.py'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    revision = git('rev-parse', 'HEAD').decode().strip()
    files = {}
    for path in git('ls-tree', '-r', '--name-only', 'HEAD').decode().splitlines():
        parts = Path(path).parts
        if len(parts) >= 3 and parts[0] == 'src' and parts[1] in PACKAGES:
            if 'validation' in parts or parts[-1] in ('VALIDATION.md', 'REQUIREMENTS.md', 'AGENTS.md'):
                continue
            files[path] = git('show', f'HEAD:{path}')
        elif path.startswith('deploy/') and Path(path).name in TOOLS:
            files[path] = git('show', f'HEAD:{path}')
    files['README.md'] = git('show', 'HEAD:deploy/README.md')
    metadata = {'source_revision': revision, 'packages': list(PACKAGES),
                'platform': 'Ubuntu 24.04 Desktop x86_64 / ROS 2 Jazzy / Gazebo Harmonic',
                'build_required': True, 'cantonese_audio_clips': 36}
    files['RELEASE.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode()
    private_markers = (b'192.168.72.200', b'codex_ubuntu_vm', b'/home/jay/',
                       b'C:/Users/LENOVO', b'C:\\Users\\LENOVO', b'BEGIN OPENSSH PRIVATE KEY')
    for path, data in files.items():
        if any(marker in data for marker in private_markers):
            raise SystemExit('发布文件包含本机连接或私有路径：' + path)
        if path.endswith('.sh') and b'\r' in data:
            raise SystemExit('Linux启动脚本必须使用LF换行：' + path)
    checksums = ''.join(hashlib.sha256(data).hexdigest() + '  ' + path + '\n'
                        for path, data in sorted(files.items()))
    files['SHA256SUMS.txt'] = checksums.encode('utf-8')
    stamp = datetime.fromtimestamp(int(git('show', '-s', '--format=%ct', 'HEAD')), timezone.utc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            entry = zipfile.ZipInfo('heritage-guide-demo/' + path, stamp.timetuple()[:6])
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100755 if path.endswith('.sh') else 0o100644) << 16
            archive.writestr(entry, data)
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise SystemExit('ZIP校验失败')
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(args.output.suffix + '.sha256').write_bytes((digest + '  ' + args.output.name + '\n').encode())
    print(json.dumps({'file': str(args.output), 'files': len(files), 'source_revision': revision,
                      'bytes': args.output.stat().st_size, 'sha256': digest}, ensure_ascii=False))


if __name__ == '__main__':
    main()
