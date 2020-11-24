# DICOMLabeling
Applications for labelong data from the localizer of a computed tomograph.

The labeling is carried out in five parts of the human body:
* Head
* Neck
* Chest
* Abdomen
* Pelvis

Annotations for an image are written to the metadata of the processed image using overlays:

## Creating and installing virtual environment
1. I suggest creating an environment from an [environment.yml](https://github.com/AlexeyPopov1997/DICOMLabeling/blob/master/environment.yml) file (**Warning!!! You need to change `prefix` in the file**):

`conda env create -f environment.yml`

The first line of the `yml` file sets the new environment's name.

2. Activate the new environment:`conda activate DICOMLabeling`

3. Verify that the new environment was installed correctly: `conda env list`
