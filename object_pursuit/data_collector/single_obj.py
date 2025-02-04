import os
import cv2
import numpy as np
from tqdm import tqdm
from ai2thor.controller import Controller
import random
from fstring import fstring as f

# from supervisor import Supervisor_loop

class SingleObjEnv:
    def __init__(self, objectType, scene="FloorPlan1", save_dir="./data", change_pos_times=120, remove_other_object_prob=0.0, max_data_num=2000, width=572, height=572, local_executable_path = None):
        self.save_dir = save_dir
        self.change_pos_times = change_pos_times
        self.mainobjType = objectType
        self.scene = scene
        self.max_data_num = max_data_num
        self.x_display = "0"
        self.remove_other_object_prob = remove_other_object_prob
        self.controller = Controller(
            agentMode="default",
            visibilityDistance=1.2,
            scene=self.scene,
            
            # step sizes
            gridSize=0.4,
            snapToGrid=True,
            rotateStepDegrees=4,
            
            # image modalities
            renderDepthImage=True,
            renderInstanceSegmentation=True,
            
            # camera properties
            width=width,
            height=height,
            fieldOfView=30,
            
            # display
            quality='Ultra',
            local_executable_path=local_executable_path,
            x_display=self.x_display,
        )
        self.npz_data = {}
        self._collect_obj_info()
        # Supervisor_loop(self.controller)
        
    def _collect_obj_info(self):
        self.mainobjNames = []
        obj_status = self.controller.last_event.metadata["objects"]
        for obj in obj_status:
            if obj["pickupable"] and obj["objectType"]==self.mainobjType:
                self.mainobjNames.append(obj["name"])
        print(f("[INFO] for object type {self.mainobjType}, find objects: {self.mainobjNames}"))
        
    def _init_status(self, seed):
        self.controller.reset()
        self.init_status = self.controller.step(action="InitialRandomSpawn", randomSeed=seed, forceVisible=False, numPlacementAttempts=5, placeStationary=False)
        self._remove_other_object(self.init_status.metadata["objects"])
        
    def _remove_other_object(self, obj_status):
        mainobj_exist = False
        seen_types = set()
        self.mainObjId, self.mainobjType = next(
                (obj["objectId"], obj["objectType"]) for obj in self.controller.last_event.metadata["objects"]
                if obj["name"] == self.mainobjName
            )
        random.shuffle(obj_status)
        for obj in obj_status:
            # if obj["pickupable"]:
            #     print(obj["objectType"], obj["name"])
            if obj["pickupable"] and obj["name"] != self.mainobjName:
                # if an object Type has been seen, remove other instance
                if obj["objectType"] in seen_types:
                    self.controller.step(
                        action="DisableObject",
                        objectId=obj["objectId"]
                    )
                else:
                    seen_types.add(obj["objectType"])
            elif obj["name"] == self.mainobjName:
                mainobj_exist = True
        if not mainobj_exist:
            print(f("[Warning] main object {self.mainobjName} not exist in scene {self.scene}"))
        else:
            print(f("[INFO] current info: obj-type {self.mainobjType}, obj-name {self.mainobjName}, obj-id {self.mainObjId}"))
            
    def _collectData(self, seed, horizons):
        try:
            if horizons is None:
                horizons = [-30, 0, 30, 60]
                horizon_offset = random.randint(0, 29)
                horizons = [h+horizon_offset for h in horizons if h+horizon_offset <= 60]
            self._init_status(seed)
            event = self.controller.step(
                action="GetInteractablePoses",
                objectId=self.mainObjId,
                horizons=horizons
            )
            poses = event.metadata["actionReturn"]
            print(f("search complete, find {len(poses)} available position, seed {seed}"))
            num = 0
            for pose in tqdm(poses):
                state = self.controller.step("TeleportFull", **pose)
                frame = state.frame
                depth_frame = state.depth_frame
                mask = state.instance_masks[self.mainObjId]
                name = f("{self.scene}_seed_{'%04d' % seed}_num_{'%06d' % num}")
                self._saveImg(name, state.cv2img, depth_frame, mask)
                # self.npz_data[name] = {"frame": frame, "depth": depth_frame, "mask": mask}
                num += 1
            return num
        except Exception as e:
            print("[Error] catch an Error! ", e)
        
    def _saveImg(self, name, cv_img, depth_frame, mask):
        dirs = [os.path.join(self.outdir, sub_dir) for sub_dir in ["imgs", "depths", "masks"]]
        for d in dirs:
            if not os.path.exists(d):
                os.mkdir(d)
        converted_mask = np.zeros(mask.shape)
        for i in range(mask.shape[0]):
            for j in range(mask.shape[1]):
                if mask[i][j]:
                    converted_mask[i][j] = 255
        cv2.imwrite(os.path.join(dirs[0], name+".png"), cv_img)
        # cv2.imwrite(os.path.join(dirs[1], name+".png"), depth_frame)
        # np.savez(os.path.join(dirs[1], name), depth_frame)
        cv2.imwrite(os.path.join(dirs[2], name+".png"), converted_mask)
        
    def _saveNPZ(self, name, frame, depth_frame, mask):
        dir = os.path.join(self.outdir, "npz")
        if not os.path.exists(dir):
            os.mkdir(dir)
        npz_dict = {"frame": frame, "depth": depth_frame, "mask": mask}
        np.savez(os.path.join(dir, name+".npz"), **npz_dict)
        
    def genData(self, horizons=None):
        for obj in self.mainobjNames:
            print(f("[INFO] start to generate data for {obj}"))
            self.mainobjName = obj
            count = 0
            self.outdir = os.path.join(self.save_dir, f("data_{self.scene}_{self.mainobjName}"))
            if not os.path.exists(self.outdir):
                os.mkdir(self.outdir)
            for i in range(self.change_pos_times):
                num = self._collectData(i, horizons)
                if num is not None:
                    count += num
                if count > self.max_data_num:
                    break
                # np.savez(os.path.join(self.outdir, f("ithor_single_{self.scene}.npz")), **self.npz_data)
        
    
if __name__ == "__main__":
    obj = 'Pan'
    env = SingleObjEnv(objectType=obj, scene=f("FloorPlan2", change_pos_times=200, remove_other_object_prob=0.8, max_data_num=2000, save_dir=f("/data/",local_executable_path="../ithor/unity/builds/thor-Linux64-local/thor-Linux64-local")))
    env.genData()
    