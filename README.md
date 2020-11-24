# DICOMLabeling
Applications for labeling data from the localizer of a computed tomograph.

The labeling is carried out in five parts of the human body:
* Head
* Neck
* Chest
* Abdomen
* Pelvis

![DICOMLabeling](https://github.com/AlexeyPopov1997/DICOMLabeling/blob/master/pictures/labeling.png?raw=true)

Annotations for an image are written to the metadata of the processed image using overlays:
![Metadata](https://github.com/AlexeyPopov1997/DICOMLabeling/blob/master/pictures/metadata.png?raw=true)

The labeling results can be viewed using [Weasis](https://github.com/nroduit/Weasis).
![Metadata](https://github.com/AlexeyPopov1997/DICOMLabeling/blob/master/pictures/result.png?raw=true)

## Creating and installing virtual environment
1. I suggest creating an environment from an [environment.yml](https://github.com/AlexeyPopov1997/DICOMLabeling/blob/master/environment.yml) file (**You need to change `prefix` in the file**):
```sh
conda env create -f environment.yml
```

The first line of the `yml` file sets the new environment's name.

2. Activate the new environment: 
```sh
conda activate DICOMLabeling
```

3. Verify that the new environment was installed correctly: 
```sh
conda env list
```
