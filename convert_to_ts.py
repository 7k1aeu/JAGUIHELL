from glyphs import GLYPHS

with open('glyphs.ts', 'w', encoding='utf-8') as f:
    f.write("export const GLYPHS: { [key: string]: number[] } = {\n")
    for k, v in GLYPHS.items():
        arr = ', '.join(f'0x{col:04x}' for col in v)
        f.write(f"  '{k}': [{arr}],\n")
    f.write("};\n")