"""Рендер анимации сборки в Blender по JSON из tools/grid_anim.py.

  Blender -b -P tools/anim_blender.py -- build/anim_3х3.json step/6/3х3/сборка.mp4
  Blender -b -P tools/anim_blender.py -- build/anim_3х3.json build/кадр_#.png --stills 5,20,40 --res 960x540

Без -b скрипт только строит сцену (для просмотра в интерфейсе).
"""
import argparse, json, math, sys
import bpy

FPS = 30
MM = 0.001
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
FONT_B = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


MATS = {}


def material(rgb, alpha=1.0, emit=False):
    key = (tuple(rgb), alpha, emit)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(f'mat_{len(MATS)}')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    col = (*[lin(c) for c in rgb], 1)
    if emit:
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = col
        nt.links.new(em.outputs[0], out.inputs[0])
    else:
        bsdf.inputs['Base Color'].default_value = col
        bsdf.inputs['Roughness'].default_value = 0.75 if rgb[0] != rgb[2] else 0.4
        if alpha < 1:
            bsdf.inputs['Alpha'].default_value = alpha
            for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
                try:
                    setattr(m, attr, val)
                    break
                except (AttributeError, TypeError):
                    pass
    MATS[key] = m
    return m


def frame(t):
    return round(t * FPS) + 1


def keyed_visibility(ob, t_show, t_hide=None):
    for f, hide in ((1, True), (frame(t_show), False)) + (((frame(t_hide), True),) if t_hide is not None else ()):
        ob.hide_render = ob.hide_viewport = hide
        ob.keyframe_insert('hide_render', frame=f)
        ob.keyframe_insert('hide_viewport', frame=f)


def build_parts(data):
    coll = bpy.data.collections.new('дом')
    bpy.context.scene.collection.children.link(coll)
    for p in data['parts']:
        v, f = p['v'], p['f']
        me = bpy.data.meshes.new(p['name'])
        me.from_pydata([(v[i] * MM, v[i + 1] * MM, v[i + 2] * MM) for i in range(0, len(v), 3)], [],
                       [f[i:i + 3] for i in range(0, len(f), 3)])
        me.materials.append(material(p['color'], p['alpha']))
        ob = bpy.data.objects.new(p['name'], me)
        coll.objects.link(ob)
        keys = p['keys']
        for t, dx, dy, dz in keys:
            ob.location = (dx * MM, dy * MM, dz * MM)
            ob.keyframe_insert('location', frame=frame(t))
        if keys[0][0] > 0:
            keyed_visibility(ob, keys[0][0])


def build_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('мир')
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.55, 0.68, 0.85, 1)
    bg.inputs['Strength'].default_value = 0.9
    sc.world = w
    sun = bpy.data.lights.new('солнце', 'SUN')
    sun.energy = 3.2
    sun.angle = math.radians(4)
    so = bpy.data.objects.new('солнце', sun)
    so.rotation_euler = (math.radians(50), 0, math.radians(-30))
    sc.collection.objects.link(so)
    bpy.ops.mesh.primitive_plane_add(size=400, location=(1.6, 1.6, 0))
    gr = bpy.context.active_object
    gr.name = 'земля'
    gr.data.materials.append(material((112, 128, 92)))


def build_camera(data):
    sc = bpy.context.scene
    cam = bpy.data.cameras.new('камера')
    cam.lens = 35
    cam.clip_start = 0.05
    co = bpy.data.objects.new('камера', cam)
    sc.collection.objects.link(co)
    sc.camera = co
    tgt = bpy.data.objects.new('цель', None)
    sc.collection.objects.link(tgt)
    tr = co.constraints.new('TRACK_TO')
    tr.target, tr.track_axis, tr.up_axis = tgt, 'TRACK_NEGATIVE_Z', 'UP_Y'
    keys = sorted(data['camera'])
    tx, ty = (c * MM for c in data['target'])

    def at(t):
        if t <= keys[0][0]:
            return keys[0][1:]
        for a, b_ in zip(keys, keys[1:]):
            if a[0] <= t <= b_[0]:
                u = 0 if b_[0] == a[0] else (t - a[0]) / (b_[0] - a[0])
                u = u * u * (3 - 2 * u)
                return [x + (y - x) * u for x, y in zip(a[1:], b_[1:])]
        return keys[-1][1:]

    t, dur = 0.0, data['duration']
    while t <= dur + 1e-6:
        az, el, dist, tz = at(t)
        a, e = math.radians(az), math.radians(el)
        d = dist * MM
        co.location = (tx + d * math.cos(e) * math.sin(a), ty - d * math.cos(e) * math.cos(a), tz * MM + d * math.sin(e))
        tgt.location = (tx, ty, tz * MM)
        co.keyframe_insert('location', frame=frame(t))
        tgt.keyframe_insert('location', frame=frame(t))
        t += 0.25
    for ob in (co, tgt):
        for fc in fcurves(ob):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    return co


def fcurves(ob):
    act = ob.animation_data.action
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])):
        return act.fcurves
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out += list(bag.fcurves)
    return out


def text(body, size, loc, parent, font, mat):
    cu = bpy.data.curves.new('подпись', 'FONT')
    cu.body, cu.size, cu.font = body, size, font
    cu.align_x, cu.align_y = 'LEFT', 'CENTER'
    ob = bpy.data.objects.new('подпись', cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent, ob.location = parent, loc
    cu.materials.append(mat)
    return ob


def build_captions(data, cam, aspect):
    f, fb = bpy.data.fonts.load(FONT), bpy.data.fonts.load(FONT_B)
    white, grey = material((255, 255, 255), emit=True), material((215, 220, 225), emit=True)
    hw = 0.5 * 36 / 35                    # полуширина кадра на расстоянии 1 м (sensor 36, lens 35)
    hh = hw / aspect
    me = bpy.data.meshes.new('плашка')
    y0, y1 = -hh, -hh + 0.075
    me.from_pydata([(-hw, y0, 0), (hw, y0, 0), (hw, y1, 0), (-hw, y1, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(material((10, 14, 20), 0.62))
    band = bpy.data.objects.new('плашка', me)
    bpy.context.scene.collection.objects.link(band)
    band.parent, band.location = cam, (0, 0, -1.001)
    for t0, t1, title, sub in data['captions']:
        a = text(title, 0.028, (-hw + 0.03, y1 - 0.024, -1), cam, fb, white)
        b_ = text(sub, 0.0175, (-hw + 0.03, y0 + 0.020, -1), cam, f, grey)
        for ob in (a, b_):
            keyed_visibility(ob, t0, t1)


def setup_render(res, samples):
    sc = bpy.context.scene
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    try:
        sc.eevee.taa_render_samples = samples
    except AttributeError:
        pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    try:
        sc.view_settings.view_transform = 'Standard'
    except TypeError:
        pass


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('json')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--stills', default='')
    ap.add_argument('--res', default='1920x1080')
    ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--cam', default='', help='az,el,dist,tz — неподвижная камера (для отладки кадров)')
    a = ap.parse_args(argv)
    res = tuple(int(x) for x in a.res.split('x'))
    data = json.load(open(a.json))
    if a.cam:
        data['camera'] = [[0, *map(float, a.cam.split(','))]]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    build_world()
    build_parts(data)
    cam = build_camera(data)
    build_captions(data, cam, res[0] / res[1])
    setup_render(res, a.samples)
    sc.frame_start, sc.frame_end = 1, frame(data['duration'])
    print(f'сцена: {len(data["parts"])} деталей, кадров {sc.frame_end}')
    if not bpy.app.background or not a.out:
        return
    if a.stills:
        sc.render.image_settings.file_format = 'PNG'
        for t in a.stills.split(','):
            sc.frame_set(frame(float(t)))
            sc.render.filepath = a.out.replace('#', t)
            bpy.ops.render.render(write_still=True)
        return
    im = sc.render.image_settings
    try:
        im.media_type = 'VIDEO'
    except (AttributeError, TypeError):
        pass
    im.file_format = 'FFMPEG'
    sc.render.ffmpeg.format, sc.render.ffmpeg.codec = 'MPEG4', 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.filepath = a.out
    bpy.ops.render.render(animation=True)


main()
