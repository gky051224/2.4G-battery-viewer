"""Generate the matching vector-style Windows app icon, standard library only."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from win_icon import build_ico


def inside_round(x, y, box, radius):
    left, top, right, bottom = box
    if not (left <= x <= right and top <= y <= bottom):
        return False
    cx = min(max(x, left+radius), right-radius)
    cy = min(max(y, top+radius), bottom-radius)
    return (x-cx)**2 + (y-cy)**2 <= radius**2


def inside_polygon(x, y, points):
    result = False
    px, py = points[-1]
    for nx, ny in points:
        if (ny > y) != (py > y) and x < (px-nx)*(y-ny)/(py-ny)+nx:
            result = not result
        px, py = nx, ny
    return result


def render(size):
    result = bytearray(size*size*4)
    bg, mint, white = (23,35,43), (120,228,189), (243,255,249)
    bolt = [(34,23),(24,34),(31,34),(28,44),(40,30),(32,30)]
    samples = 4
    for y in range(size):
        for x in range(size):
            red = green = blue = alpha = 0
            for sy in range(samples):
                for sx in range(samples):
                    u = (x+(sx+.5)/samples)*64/size
                    v = (y+(sy+.5)/samples)*64/size
                    color = None
                    if inside_round(u,v,(3,3,61,61),15): color = bg
                    if inside_round(u,v,(12,21,49,44),5): color = mint
                    if inside_round(u,v,(49,28,54,37),2): color = mint
                    if inside_round(u,v,(16,25,45,40),2): color = bg
                    if inside_polygon(u,v,bolt): color = white
                    if color:
                        red+=color[0];green+=color[1];blue+=color[2];alpha+=1
            if alpha:
                i=(y*size+x)*4
                result[i:i+4]=bytes((red//alpha,green//alpha,blue//alpha,255*alpha//16))
    return bytes(result)


if __name__ == "__main__":
    target=ROOT/'assets'/'app.ico'
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(build_ico([(s,render(s)) for s in (16,20,24,32,48,64,128,256)]))
    print(target)
