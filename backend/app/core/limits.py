"""
limits.py — length caps on user text that is forwarded to Claude.

Each request that carries one of these fields can end in one or more Anthropic
calls, and chat turns replay the whole history, so an uncapped field lets any
account run up unbounded spend. The caps are enforced by the request schemas
(a longer value is rejected with a 422 before the route runs).

The frontend mirrors these numbers in ``frontend/src/lib/inputLimits.ts`` to
show a counter and block sending; ``tests/test_input_length_caps.py`` fails if
the two files disagree. Counts are characters (Python ``len``).
"""

#: A discovery chat message or a module answer.
CHAT_MESSAGE_MAX_CHARS = 4_000

#: A project's idea description, a template's extra detail, and the text sent
#: for pathway detection (the Home page sends the idea to both).
DESCRIPTION_MAX_CHARS = 10_000

#: A feature block's description.
BLOCK_DESCRIPTION_MAX_CHARS = 2_000
