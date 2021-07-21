import os
import re
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import collections
from model.coeffnet.deeplab_block.aspp import *
from model.coeffnet.deeplab_block.decoder import *
from model.deeplabv3 import backbone

class Coeffnet_Deeplab(nn.Module):
    n_channels = 3
    n_classes = 1
    
    def __init__(self, base_dir, device):
        super(Coeffnet_Deeplab, self).__init__()
        self.base_dir = base_dir
        self.device = device
        self.base_num, self.aspp_bases, self.decoder_bases = self._parse_base_files(base_dir, device)
        print("The number of base: ", self.base_num)
        
        # build coeffs
        self.init_value = 1.0/math.sqrt(self.base_num)
        self.coeffs = nn.Parameter(torch.randn(self.base_num))
        torch.nn.init.constant_(self.coeffs, self.init_value)
        print("init coeff-", self.coeffs)
        
        # combine function
        self.combine_func = self._linear
        
        # build backbone
        self.backbone = backbone.build_backbone('resnetsub', 16, nn.BatchNorm2d)
        self.backbone.load_state_dict(
            torch.load("./pretrained/backbone.pth", map_location=device)
        )
        # freeze backbone
        for param in self.backbone.parameters():
            param.requires_grad = False
        
        
    def _parse_base_files(self, base_dir, device):
        base_files = [os.path.join(base_dir, file) for file in os.listdir(base_dir) if file.endswith(".pth")]
        print("base files: ", base_files)
        base_num = len(base_files)
        aspp_weights = collections.OrderedDict()
        decoder_weights = collections.OrderedDict()
        for f in base_files:
            state_dict = torch.load(f, map_location=device)
            for param in state_dict:
                # print(param, state_dict[param].size(), type(state_dict))
                if param.startswith("backbone"):
                    pass
                elif param.startswith("aspp"):
                    if param not in aspp_weights:
                        aspp_weights[param] = [state_dict[param]]
                    else:
                        assert(state_dict[param].size() == aspp_weights[param][0].size())
                        aspp_weights[param].append(state_dict[param])
                elif param.startswith("decoder"):
                    if param not in decoder_weights:
                        decoder_weights[param] = [state_dict[param]]
                    else:
                        assert(state_dict[param].size() == decoder_weights[param][0].size())
                        decoder_weights[param].append(state_dict[param])
                else:
                    print(f"[Warning] find illegal network parameter: {param}")
        
        self._trans_bn(aspp_weights, base_num)
        self._trans_bn(decoder_weights, base_num)
        return base_num, aspp_weights, decoder_weights
    
    
    def _trans_bn(self, param_dict, base_num, epsilon=1e-05):
        """translate bn(batch norm) weights to linear weights

        Args:
            param_dict (dict): network parameter dict
        """
        # get bn names
        bn_names = set()
        for param in param_dict:
            try:
                # here we use running_mean to judge whether it is batchnorm, but there are other operations has this attribute too
                bn_name = re.match(r'(.+)\.running\_mean', param).group(1)
                assert((bn_name+".weight") in param_dict)
                assert((bn_name+".bias") in param_dict)
                assert((bn_name+".running_var") in param_dict)
                bn_names.add(bn_name)
            except Exception:
                pass
        
        for bn in bn_names:
            param_dict[bn+".weight_prime"] = []
            param_dict[bn+".bias_prime"] = []
            for i in range(base_num):
                shape = param_dict[bn + ".weight"][i].size()
                var = torch.div(torch.ones(shape).to(self.device), (param_dict[bn + ".running_var"][i]+torch.ones(shape).to(self.device)*epsilon).sqrt())
                weight_var = torch.mul(param_dict[bn + ".weight"][i], var)
                param_dict[bn+".weight_prime"].append(weight_var)
                param_dict[bn+".bias_prime"].append(param_dict[bn + ".bias"][i]-torch.mul(param_dict[bn + ".running_mean"][i], weight_var))
        
    
    
    def _linear(self, bases, coeffs):
        assert len(bases) == len(coeffs)
        n = len(bases)
        if n > 0:
            res = bases[0] * coeffs[0]
            for i in range(1, n):
                res += bases[i] * coeffs[i]
            return res
        else:
            raise ValueError
    
    def _update_weights(self):
        aspp_weights = collections.OrderedDict()
        decoder_weights = collections.OrderedDict()
        for param in self.aspp_bases:
            aspp_weights[param] = self.combine_func(self.aspp_bases[param], self.coeffs)
        for param in self.decoder_bases:
            decoder_weights[param] = self.combine_func(self.decoder_bases[param], self.coeffs)
        return aspp_weights, decoder_weights
    
    def forward(self, input):
        # update network parameters:
        new_aspp, new_decoder = self._update_weights()
        
        # backbone forward
        x, low_level_feat = self.backbone(input)
        
        # aspp forward
        x = ASPP("aspp", x, new_aspp, output_stride=16)
        
        # decoder forward
        x = Decoder("decoder", x, low_level_feat, new_decoder)
        x = F.interpolate(x, size=input.size()[2:], mode='bilinear', align_corners=True)
        
        return x
        
        
        