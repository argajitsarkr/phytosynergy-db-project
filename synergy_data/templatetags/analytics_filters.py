from django import template

register = template.Library()


@register.filter
def heatmap_color(fic_value):
    """
    Return an RGB background color for a heatmap cell based on FIC index.
    Green (synergy) → Yellow (additive) → Orange (indifference) → Red (antagonism)
    """
    if fic_value is None:
        return '#f0f0f0'

    try:
        v = float(fic_value)
    except (TypeError, ValueError):
        return '#f0f0f0'

    # Clamp to 0–5 range for coloring
    v = max(0.0, min(v, 5.0))

    # Define color stops: (fic_value, R, G, B)
    # 0.0  → dark green  (27, 94, 32)
    # 0.5  → green       (76, 175, 80)
    # 1.0  → yellow      (255, 241, 118)
    # 2.0  → orange      (255, 152, 0)
    # 4.0+ → dark red    (198, 40, 40)
    stops = [
        (0.0,  27,  94,  32),
        (0.5,  76, 175,  80),
        (1.0, 255, 241, 118),
        (2.0, 255, 152,   0),
        (4.0, 198,  40,  40),
        (5.0, 198,  40,  40),
    ]

    # Find the two stops to interpolate between
    for i in range(len(stops) - 1):
        v0, r0, g0, b0 = stops[i]
        v1, r1, g1, b1 = stops[i + 1]
        if v <= v1:
            if v1 == v0:
                t = 0
            else:
                t = (v - v0) / (v1 - v0)
            r = int(r0 + t * (r1 - r0))
            g = int(g0 + t * (g1 - g0))
            b = int(b0 + t * (b1 - b0))
            return f'rgb({r},{g},{b})'

    return 'rgb(198,40,40)'
