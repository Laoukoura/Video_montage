"""Version B : 16:9, 1920x1080 (YouTube)."""
import compose


def render(cuts, plan, analyse, cut_path, **kw):
    return compose.compose("h", cuts, plan, analyse, cut_path, **kw)
