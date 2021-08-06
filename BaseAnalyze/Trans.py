import os
import torch
import numpy as np

def _neglect(param, prefix_neglect, suffix_neglect):
    assert(isinstance(param, str))
    for prefix in prefix_neglect:
        if param.startswith(prefix):
            return True
    for suffix in suffix_neglect:
        if param.endswith(suffix):
            return True
    return False

def weight2vec(weight_file, prefix_neglect=[], suffix_neglect=[]):
    state_dict = torch.load(weight_file, map_location='cpu')
    vec_list = []
    for param in state_dict:
        if not _neglect(param, prefix_neglect, suffix_neglect):
            vec = state_dict[param].numpy().ravel()
            vec_list.append(vec)
    
    return np.concatenate(vec_list)

def z2vec(base_dir, save_dir):
    file_list = [os.path.join(base_dir, file) for file in os.listdir(base_dir) if file.endswith(".json")]
    for file in file_list:
        z = torch.load(file, map_location='cpu')['z']
        print(file, ":", torch.norm(z))
        np.save(os.path.join(save_dir, os.path.splitext(os.path.basename(file))[0]), z.numpy())
        
def vec2z(vec_file, z_file):
    vec = np.load(vec_file)
    state_dict = {'z': torch.from_numpy(vec)}
    print(state_dict['z'].size())
    torch.save(state_dict, z_file)
    
def save_vec(weight_vec, dir, name="weight"):
    np.save(os.path.join(dir, name), weight_vec)
    
def viz_weight(weight_file):
    state_dict = torch.load(weight_file, map_location='cpu')
    for param in state_dict:
        print(param, state_dict[param].size())
    # for param in state_dict['weights']:
    #     print(param, state_dict['weights'][param].size())
    # print(state_dict['z'])


if __name__ == "__main__":
    # obj = "Pot"
    # name = "fp2_"+obj
    # weight_vec = weight2vec(f"/data/pancy/object_pursuit/checkpoints/pretrained_backbone/checkpoints_{obj}_FP2/MODEL_{obj}_fp2.pth", ["backbone"], ["running_mean", "running_var", "num_batches_tracked"])
    # weight_vec = weight2vec(f"../Segmentation/INTERRUPTED.pth", ["backbone"], ["running_mean", "running_var", "num_batches_tracked"])
    # save_vec(weight_vec, dir="./Vec", name="Random")
    # print(weight_vec.shape)
    # viz_weight("../Segmentation/checkpoints_coeff_Egg/Best.pth")
    z2vec("../Segmentation/Bases", "./Vec")
    # obj = 'Kettle'
    # vec2z(f'./Vec/{obj}.npy', f'../Segmentation/Bases/{obj}.json')