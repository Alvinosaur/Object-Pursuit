import torch
import random
from tqdm import tqdm

def get_pos_weight(dataset, max_sample_num=200):
    print("[INFO] Start scanning masks to get the pos weight")
    if len(dataset) > 0:
        sample = dataset[0]['mask']
        total_pixel = sample.size(0) * sample.size(1) * sample.size(2)
    pos_weights = []
    if len(dataset) > max_sample_num:
        samples = random.sample(range(len(dataset)), max_sample_num)
    else:
        samples = range(len(dataset))
    for i in tqdm(samples):
        mask = dataset[i]['mask']
        nonzero_num = torch.nonzero(mask).size(0)
        if nonzero_num > 0:
            pos_weights.append((total_pixel-nonzero_num)/nonzero_num)
    return sum(pos_weights)/len(pos_weights)
