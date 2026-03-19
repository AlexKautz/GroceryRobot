*Here we keep track of different papers related to our work. If you can keep a PDF copy in the documents section.*

### RoboCart: toward robot-assisted navigation of grocery stores by the visually impaired
* Link: [IEEE](https://ieeexplore.ieee.org/abstract/document/1545107)
* PDF: [[RoboCart_toward_robot-assisted_navigation_of_grocery_stores_by_the_visually_impaired.pdf|Local]]
* Notes:
	* RoboCart focuses on navigating a store
	* RoboCart uses RFID tags to identify specific objects rather than computer vision.
	* "Knowledge engineering for the path planner is done in OpenCyc, a free knowledge engineering tool from the Cyc Corporation that allows one to represent common sense knowledge using first order logic"

### Deep Learning based Object Recognition for Robot picking task
* Link: [https://ieeexplore.ieee.org/abstract/document/7053853](https://dl.acm.org/doi/abs/10.1145/3164541.3164628)
* PDF: [ACM](https://dl.acm.org/doi/epdf/10.1145/3164541.3164628) [[Deep_Learning_Based_Object_Recognition_for_Robot_Picking_Task.pdf|Local]]
* About object recognition in cluttered scene and success using RESNET.
* YOLO
	* "you only look once" - a basic shallow convolutional neural network. It's relatively fast, but this paper finds that it's only accurate enough to determine whether an object is in a image, not where in the image the object is. It attempts to draw a bounding box around an object after it is found in the image. See - Joseph Redmon, Santosh Kumar Divvala, Ross B. Girshick, and Ali Farhadi. 2015. You Only Look Once: Unified, Real-Time Object Detection. (2015). http://arxiv.org/abs/1506.02640
* RESNET
	* a larger neural network that also does object recognition. This one segments the image, creating a "mask" that surrounds an object. Slower than YOLO. The paper finds this one is useful!
* Thoughts:
	* for our uses, I think RESNET can be very powerful.  Assuming we are a "robotic arm putting away groceries", we will have a fixed window where we look for groceries. In that case we can wait them multiple seconds to run RESNET once before moving the arm.
	* YOLO can also be used as a faster initial pass to see if the object is in the camera view in the first place.

### Object detection and mapping for service robot tasks
* Link: https://www.cambridge.org/core/journals/robotica/article/object-detection-and-mapping-for-service-robot-tasks/212A50021787D5905AF0766231D55A5B
* PDF: [[object-detection-and-mapping-for-service-robot-tasks.pdf|Local]]
* Paper studies mobile robot that autonomously navigates dometic environment, builds map, & detects predefined objects. Some relevant info on object detection vs object recognition.

### Grocery product detection and recognition
* Link: [Science Direct](https://www.sciencedirect.com/science/article/pii/S0957417417301227)
* PDF: [[Grocery_Product_Detection_and_Recognition.pdf|Local]]
*  this paper seeks to achieve similar results to [[#Object detection and mapping for service robot tasks]] but using more traditional computer vision methods
* phase 1 - pre-selection
	* does traditional binarization and edgepoint selection.
	* relies on the background of the objects being darker than the objects (like on a store shelf)
		* if we use this method, we'll have to consider how our groceries look on the counter before the robotic arm reaches for them.
* phase 2 - fine-selection
	* Bag of Words technique - these are "image words", vectors representing features of an image, similar to how [word vectors](https://en.wikipedia.org/wiki/Word2vec) represent actual words.
	* Deep Neural Networks approach - Uses AlexNet on black and white images.
		* I think we could probably find a better pre-trained model nowadays, certainly [[#Object detection and mapping for service robot tasks]] - RESNET would be a good option
* phase 3 - post processing
	* phase 1 and 2 produce multiple bounding boxes for each object. This just clusters them into a singular box.