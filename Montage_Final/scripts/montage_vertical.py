"""Version A : 9:16, 1080x1920 (Reels / TikTok / Shorts)."""
import compose


def render(cuts, plan, analyse, cut_path, **kw):
    return compose.compose("v", cuts, plan, analyse, cut_path, **kw)
