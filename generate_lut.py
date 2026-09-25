import os
import colorsys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LUT_DIR = os.path.join(SCRIPT_DIR, "assets", "luts")
os.makedirs(LUT_DIR, exist_ok=True)
LUT_PATH = os.path.join(LUT_DIR, "lofi_cinematic.cube")
SIZE = 33

def s_curve(x):
    # Filmic S-curve: softens highlights and deepens rich tones without crushing darks
    return x * x * (3.0 - 2.0 * x) * 0.30 + x * 0.70

def generate():
    lines = []
    lines.append('TITLE "Lofi_Cozy_Cinematic"\n')
    lines.append(f'LUT_3D_SIZE {SIZE}\n')

    vals = [i / (SIZE - 1) for i in range(SIZE)]

    for b_val in vals:
        for g_val in vals:
            for r_val in vals:
                # 1. Apply gentle film S-curve
                r = s_curve(r_val)
                g = s_curve(g_val)
                b = s_curve(b_val)
                
                # 2. Convert to HSV for warm cozy styling
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                
                # Boost saturation slightly for cozy anime / nature warmth (+8%)
                s = min(1.0, s * 1.08)
                
                # Convert back to RGB
                ro, go, bo = colorsys.hsv_to_rgb(h, s, v)
                
                # 3. Add warm golden/amber cozy glow to highlights and midtones
                if v > 0.30:
                    w = ((v - 0.30) / 0.70) * 0.04
                    ro = min(1.0, ro + w * 1.1)
                    go = min(1.0, go + w * 0.6)
                    bo = max(0.0, bo - w * 0.4)
                    
                lines.append(f"{ro:.6f} {go:.6f} {bo:.6f}\n")

    with open(LUT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[SUCCESS] Wrote {len(lines)} lines to {LUT_PATH}")

if __name__ == "__main__":
    generate()
