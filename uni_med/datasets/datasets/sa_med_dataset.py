import os
import json
import random

import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset


class ReferSAMedDataset(Dataset):
    def __init__(self, vis_processor, text_processor, image_dir, region_dir):
        """
        data_dir (string): Root directory of images (e.g. coco/images/)
        """

        self.vis_processor = vis_processor
        self.text_processor = text_processor
        self.image_dir = image_dir

        self.regions = []
        for modality in os.listdir(region_dir):
            # from tqdm import tqdm
            for region_name in os.listdir(os.path.join(region_dir, modality)):
            # for region_name in tqdm(os.listdir(os.path.join(region_dir, modality))):
                image_id = region_name[:-5]
                with open(os.path.join(region_dir, modality, region_name), 'r') as f:
                    regions = json.load(f)
                    for region in regions:
                        region = list(region.items())[0]
                        self.regions.append({
                            'image_id': image_id,
                            'modality': modality,
                            'object': region[0],
                            'bbox': region[1]
                        })

        self.instruction_pool = [
            "[refer] {}",
            "[refer] give me the location of {}",
            "[refer] where is {} ?",
            "[refer] from this image, tell me the location of {}",
            "[refer] the location of {} is",
            "[refer] could you tell me the location for {} ?",
            "[refer] where can I locate the {} ?",
        ]


    def __len__(self):
        return len(self.regions)

    def preprocess(self, index):
        region = self.regions[index]
        image_path = os.path.join(self.image_dir, region["modality"], region["image_id"] + ".png")
        image = Image.open(image_path).convert("RGB")
        image_orig_size = image.size
        image = self.vis_processor(image)
        image_new_size = [100,100]

        sample_sentence = region['object']
        refer_sentence = self.text_processor(sample_sentence)

        bbox = region['bbox']
        bbox = [
            bbox[0] / image_orig_size[0] * image_new_size[0],
            bbox[1] / image_orig_size[1] * image_new_size[1],
            (bbox[0] + bbox[2]) / image_orig_size[0] * image_new_size[0],
            (bbox[1] + bbox[3]) / image_orig_size[1] * image_new_size[1]
        ]
        bbox = [int(x) for x in bbox]
        bbox = "{{<{}><{}><{}><{}>}}".format(*bbox)
        return {
            "image": image,
            "refer_sentence": refer_sentence,
            "bbox": bbox,
            "image_id": region['image_id'],
        }

    def __getitem__(self, index):
        data = self.preprocess(index)
        instruction = random.choice(self.instruction_pool).format(data['refer_sentence'])

        instruction = "<Img><ImageHere></Img> {} ".format(instruction)

        return {
            "image": data['image'],
            "instruction_input": instruction,
            "answer": data['bbox'],
            "image_id": data['image_id'],
        }


class InvReferSAMedDataset(ReferSAMedDataset):
    def __init__(self, *args, **kwargs):
        super(InvReferSAMedDataset, self).__init__(*args, **kwargs)

        self.instruction_pool = [
            "[identify] {}",
            "[identify] what object is in this location {}",
            "[identify] identify the object present at this location {}",
            "[identify] what is it in {}",
            "[identify] describe this object in {}",
            "[identify] this {} is",
            "[identify] the object in {} is",
            ]

    def __getitem__(self, index):
        data = self.preprocess(index)

        instruction = random.choice(self.instruction_pool).format(data['bbox'])

        instruction = "<Img><ImageHere></Img> {} ".format(instruction)
        
        return {
            "image": data['image'],
            "instruction_input": instruction,
            "answer": self.text_processor(data['refer_sentence']),
            "image_id": data['image_id'],
        }


class ReferSAMedDataset_Eval(Dataset):
    def __init__(self, vis_processor, text_processor, image_dir, region_dir):
        self.vis_processor = vis_processor
        self.text_processor = text_processor
        self.image_dir = image_dir

        self.regions = []
        for modality in os.listdir(region_dir):
            for region_name in os.listdir(os.path.join(region_dir, modality)):
                image_id = region_name[:-5]
                with open(os.path.join(region_dir, modality, region_name), 'r') as f:
                    regions = json.load(f)
                    for region in regions:
                        region = list(region.items())[0]
                        self.regions.append({
                            'image_id': image_id,
                            'modality': modality,
                            'object': region[0],
                            'bbox': region[1]
                        })
    
    def __len__(self):
        return len(self.regions)
    
    def __getitem__(self, idx):
        data = self.regions[idx]
        object = self.text_processor(data['object'])
        bbox = torch.Tensor(data['bbox'])
        image_path = os.path.join(self.image_dir, data["modality"], data["image_id"] + ".png")
        image = Image.open(image_path).convert('RGB')
        image_size = torch.Tensor(image.size)
        image = self.vis_processor(image)
        question = f"[refer] give me the location of {object}"
        return image, question, data['image_id'], bbox, image_size


class InvReferSAMedDataset_Eval(ReferSAMedDataset_Eval):
    def __init__(self, *args, **kwargs):
        super(InvReferSAMedDataset_Eval, self).__init__(*args, **kwargs)

    def __getitem__(self, idx):
        data = self.regions[idx]

        object = self.text_processor(data['object'])
        image_path = os.path.join(self.image_dir, data["modality"], data["image_id"] + ".png")
        image = Image.open(image_path).convert("RGB")
        image_orig_size = image.size
        image = self.vis_processor(image)
        image_new_size = [100,100]

        bbox = data['bbox']
        bbox = [
            bbox[0] / image_orig_size[0] * image_new_size[0],
            bbox[1] / image_orig_size[1] * image_new_size[1],
            (bbox[0] + bbox[2]) / image_orig_size[0] * image_new_size[0],
            (bbox[1] + bbox[3]) / image_orig_size[1] * image_new_size[1]
        ]
        bbox = [int(x) for x in bbox]
        bbox = "{{<{}><{}><{}><{}>}}".format(*bbox)
        question = f"[identify] what object is in this location {bbox}"
        
        return image, question, data['image_id'], object

