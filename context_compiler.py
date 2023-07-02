import json

import src.common as common
from itertools import chain
import nlpaug.augmenter.word as naw
from tqdm import tqdm

CONFIG = common.CONFIG["context_compiler"]

if __name__ == "__main__":
    output = {"data": []}

    for file in CONFIG["files"]:
        with open(f"{file}") as f:
            print(f"Loading {file}...")
            new_context = json.load(f)

        aug = naw.SynonymAug(aug_p=0.2, aug_max=None)

        for intent in new_context['intents'].keys():
            matches = new_context['intents'][intent]['matches']
            matches_aug = list(chain(*[aug.augment(matches) for _ in range(7)]))
            new_context['intents'][intent]['matches'].extend(matches_aug)

        output["data"].append(new_context)


    with open(f"{CONFIG['output_file']}", "w") as f:
        json.dump(output, f)
