import re

async def aexec(ctx, bot, code):
    # Make an async function with the code and `exec` it
    exec(
        f'async def __ex(ctx, bot): ' +
        ''.join(f'\n {l}' for l in code.split('\n'))
    )

    # Get `__ex` from local variables, call it and return the result
    return await locals()['__ex'](ctx, bot)


def mention_to_id(mention):
    if members := re.findall('<@\!([0-9]+)?>', mention):
        return [int(member) for member in members]
    else:
        return None
