from collections import defaultdict
import emoji_data_python


MAX_VERSION = 10.0


def get_category_order():
    '''Return the categories in the order want to render them in'''
    return [
        'Smileys & Emotion',
        'People & Body',
        'Animals & Nature',
        'Food & Drink',
        'Objects',
        'Activities',
        'Travel & Places',
        'Symbols',
        'Flags'
    ]


def get_emojis_by_category():
    categories = defaultdict(list)

    for emoji in emoji_data_python.emoji_data:
        if (float(emoji.added_in) > MAX_VERSION):
            continue
        categories[emoji.category].append(emoji)

    for category_key in categories.keys():
        categories[category_key] = sorted(
            categories[category_key],
            key=lambda x: x.sort_order
        )

    return categories
