#!/usr/bin/env python3
"""Оставляет в geoip.dat/geosite.dat только перечисленные категории.

Оба файла — protobuf-сообщения вида `repeated Entry entry = 1`, где первым
полем каждой записи идёт строковый код категории. Записи копируются побайтово,
поэтому вложенная структура (домены, атрибуты, CIDR) сохраняется как есть.
"""

import argparse
import hashlib
import sys


def read_varint(buf, pos):
    result = shift = 0
    while True:
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return result, pos


def write_varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def iter_entries(blob):
    """Отдаёт (код категории, сырые байты записи без тега и длины)."""
    pos = 0
    while pos < len(blob):
        key, pos = read_varint(blob, pos)
        if key >> 3 != 1 or key & 7 != 2:
            raise ValueError(f"неожиданное поле {key >> 3} на смещении {pos}")
        length, pos = read_varint(blob, pos)
        entry = blob[pos:pos + length]
        pos += length

        inner_key, inner_pos = read_varint(entry, 0)
        if inner_key >> 3 != 1 or inner_key & 7 != 2:
            raise ValueError("в записи нет строкового кода категории")
        code_len, inner_pos = read_varint(entry, inner_pos)
        code = entry[inner_pos:inner_pos + code_len].decode("utf-8")
        yield code, entry


def trim(blob, wanted):
    wanted_upper = {name.upper() for name in wanted}
    kept, found = bytearray(), set()
    for code, entry in iter_entries(blob):
        if code.upper() in wanted_upper:
            kept += b"\x0a" + write_varint(len(entry)) + entry
            found.add(code.upper())
    return bytes(kept), found, wanted_upper - found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument("categories", nargs="+")
    parser.add_argument("--sha256", action="store_true",
                        help="дополнительно записать <target>.sha256sum")
    parser.add_argument("--strict", action="store_true",
                        help="завершиться с ошибкой, если категория не найдена")
    args = parser.parse_args()

    blob = open(args.source, "rb").read()
    kept, found, missing = trim(blob, args.categories)

    for name in sorted(missing):
        print(f"не найдено: {name}", file=sys.stderr)
    if missing and args.strict:
        return 1

    with open(args.target, "wb") as handle:
        handle.write(kept)

    if args.sha256:
        digest = hashlib.sha256(kept).hexdigest()
        basename = args.target.rsplit("/", 1)[-1]
        with open(args.target + ".sha256sum", "w") as handle:
            handle.write(f"{digest}  {basename}\n")

    print(f"{args.source}: {len(blob) / 1e6:.2f} МБ -> "
          f"{args.target}: {len(kept) / 1e6:.2f} МБ, "
          f"категорий {len(found)} из {len(args.categories)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
