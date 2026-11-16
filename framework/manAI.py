"""
doas -su mylife.root
manAI utils
"""

from . import *

manAI_talks: dict[str, list[Callable[[], str | list | None]]] = {}

@register("manAI")
def manAI(args: Arguments):
    sw = swget()
    callables = manAI_talks.get(sw, [])

    if not callables:
        print("(._.) To be continued...")

    for call in callables:
        ret = call()
        if not ret is None and not type(ret) == list:
            swset(ret) #type: ignore
        if not ret is None:
            swset(ret[0])
            print(f"[dim]! {ret[1]} ![/dim]")
    return None

def aiReg(storyWhere: str):
    """
    :param storyWhere: 注入点名称
    """
    def decorator(func: Callable) -> Callable:
        if not manAI_talks.get(storyWhere, []):
            manAI_talks.update({storyWhere: [func]})
        else:
            manAI_talks.get(storyWhere).append(func)
        return func

    return decorator