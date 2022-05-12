import os
from os.path import splitext
from os import listdir
import random
import numpy as np
from glob import glob
from torch.utils.data import Dataset
from PIL import Image
from torchvision import transforms

import object_pursuit.dataset.custom_transforms as tr 
# import custom_transforms as tr 

class BasicDataset(Dataset):
    def __init__(self, imgs_dir, masks_dir, resize = None, mask_suffix='', train=False, shuffle_seed=None, random_crop=False):
        self.imgs_dir = self._parse_dirs(imgs_dir)
        self.masks_dir = self._parse_dirs(masks_dir)
        self.resize = resize
        self.mask_suffix = mask_suffix
        self.random_crop = random_crop
        
        self._get_ids()
        
        if shuffle_seed is not None:
            r = random.random
            random.seed(shuffle_seed)
            random.shuffle(self.ids, random=r)
        
    def _parse_dirs(self, dirs):
        if type(dirs) == list:
            return dirs
        elif type(dirs) == str:
            return [dirs]
        else:
            return None
        
    def _random_crop(self, img, mask):
        length = min(img.size[0], img.size[1])
        bias = random.randint(0, max(img.size[0], img.size[1])-length)
        if img.size[0] > length:
            img = img.crop([bias, 0, bias+length, length])
            mask = mask.crop([bias, 0, bias+length, length])
        else:
            img = img.crop([0, bias, length, bias+length])
            mask = mask.crop([0, bias, length, bias+length])
        return img, mask
        
    def _get_ids(self):
        self.ids = [] # each data specified with a file path
        count = 0
        for img_dir in self.imgs_dir:
            if img_dir.endswith("/"):
                root = os.path.dirname(os.path.dirname(img_dir))
            else:
                root = os.path.dirname(img_dir)
            mask_dir = os.path.join(root, "masks")
            if mask_dir in self.masks_dir or (mask_dir+'/') in self.masks_dir:
                idx = [splitext(file)[0] for file in sorted(listdir(img_dir)) if (not file.startswith('.')) and (file.endswith('.jpg') or file.endswith('.png'))]
                img_dirs = [img_dir] * len(idx)
                mask_dirs = [mask_dir] * len(idx)
                self.ids += zip(idx, img_dirs, mask_dirs)
            elif os.path.isdir(self.masks_dir[count]):
                mask_dir = self.masks_dir[count]
                idx = [splitext(file)[0] for file in sorted(listdir(img_dir)) if (not file.startswith('.')) and (file.endswith('.jpg') or file.endswith('.png'))]
                img_dirs = [img_dir] * len(idx)
                mask_dirs = [mask_dir] * len(idx)
                self.ids += zip(idx, img_dirs, mask_dirs)
            else:
                print("[Warning] can't find mask dir: ", mask_dir)
            count += 1
        

    def __len__(self):
        return len(self.ids)

    @classmethod
    def preprocess(cls, pil_img, scale):
        w, h = pil_img.size
        newW, newH = int(scale * w), int(scale * h)
        assert newW > 0 and newH > 0, 'Scale is too small'
        pil_img = pil_img.resize((newW, newH))

        img_nd = np.array(pil_img)

        if len(img_nd.shape) == 2:
            img_nd = np.expand_dims(img_nd, axis=2)

        # HWC to CHW
        img_trans = img_nd.transpose((2, 0, 1))
        if img_trans.max() > 1:
            img_trans = img_trans / 255

        return img_trans
    
    def _get_idx(self, index):
        return self.ids[index]
    
    def _make_img_gt_point_pair(self, index):
        idx = self._get_idx(index)
        mask_file = glob(os.path.join(os.path.join(idx[2], idx[0] + self.mask_suffix + '.*')))
        img_file = glob(os.path.join(idx[1], idx[0] + '.*'))
        
        assert len(mask_file) == 1, \
            f("Either no mask or multiple masks found for the ID {idx}: {mask_file}")
        assert len(img_file) == 1, \
            f("Either no image or multiple images found for the ID {idx}: {img_file}")
        
        _img = Image.open(img_file[0]).convert('RGB')
        _mask = Image.open(mask_file[0])
        
        assert _img.size == _mask.size, \
            f("Image and mask {idx} should be the same size, but are {_img.size} and {_mask.size}")
        
        if self.random_crop:
            _img, _mask = self._random_crop(_img, _mask)
        
        if self.resize is not None:
            _img = _img.resize(self.resize)
            _mask = _mask.resize(self.resize)

        return _img, _mask, img_file[0], mask_file[0]

    def __getitem__(self, i):
        img, mask, img_file, mask_file = self._make_img_gt_point_pair(i)
        sample = {'image': img, 'mask': mask}
        
        sample = self.transform_tr(sample)
            
        sample['img_file'] = img_file
        sample['mask_file'] = mask_file
        return sample
        
    def transform_tr(self, sample):
        composed_transforms = transforms.Compose([
            tr.MaskExpand(),
            tr.ImgNorm(),
            # tr.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            tr.ToTensor()])
        return composed_transforms(sample)


class BasicDataset_nshot(BasicDataset):
    def __init__(self, imgs_dir, masks_dir, n=1, resize=None, mask_suffix='', train=False, shuffle_seed=None, random_crop=False):
        super().__init__(imgs_dir, masks_dir, resize=resize, mask_suffix=mask_suffix, train=train, shuffle_seed=shuffle_seed, random_crop=random_crop)
        self.n = n
        
    def _get_idx(self, index):
        return self.ids[index % self.n]

        
if __name__ == "__main__":
    # d = BasicDataset(["/data/pancy/iThor/single_obj/data_FloorPlan4_Egg/imgs/", "/data/pancy/iThor/single_obj/data_FloorPlan3_Egg/imgs/"], ["/data/pancy/iThor/single_obj/data_FloorPlan3_Egg/masks/", "/data/pancy/iThor/single_obj/data_FloorPlan4_Egg/masks/"])
    d = BasicDataset("/orion/u/pancy/data/object-pursuit/CO3D/apple/353_37348_70263/images", "/orion/u/pancy/data/object-pursuit/CO3D/apple/353_37348_70263/masks", resize=(256, 256))
    print(d[3])
