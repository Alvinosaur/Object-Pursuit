import torch
from object_pursuit.pursuit import pursuit

pursuit(z_dim=100, 
        data_dir="/orion/u/pancy/data/object-pursuit/ithor/Dataset/Train",
        output_dir="./checkpoints_random_1_threshold_0.7",
        device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        pretrained_bases=None,
        pretrained_backbone="./checkpoints_conv_small_full/checkpoint.pth",
        pretrained_hypernet="./checkpoints_conv_small_full/checkpoint.pth",
        # pretrained_bases="./checkpoints_objectpursuit_realdata_50base/Bases",
        # pretrained_backbone="./checkpoints_objectpursuit_rhino_test_backbone/checkpoint/backbone.pth",
        # pretrained_hypernet="./checkpoints_objectpursuit_realdata_50base/checkpoint/hypernet.pth",
        resize=(256, 256),
        select_strat="random",
        express_threshold=0.7,
        log_info="Data: random; threshold: 0.7")