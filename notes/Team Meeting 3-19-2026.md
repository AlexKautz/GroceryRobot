## Members
- Alex
- Keven
- Pascale
## Project Idea:
* Robot arm vs arm on a model platform
* Bag of groceries vs a line up of groceries
	* Bag can lead to problems, but is more realistic
	* 3rd option, use a shallow box
		* "One robot brings the box, another opens it and gets the items"
		* Start simpler, where items are not ontop of each other, then move to a larger.
		* We controll the background/ bottom of the box
			* Place localization tags undernathe
* A question of overall scope
	* Manipulation is the priority
	* How realistic is the setting?
		* represented grocerie items
* We do not know where the objects are ahead of time

### Semantic segmetation vs pointcloud segmentation
* Where on a object do we grab.
### Grippers
* Sole Grasping - Can only grasp
* Suction Grasping
* Multi-functinal grasper.
## Topics
We reviewed the different topics we would focus on
* Alex
	* Computer vision
* Keven
	* Manipulation
* Pascale
	* Planning
	* Classification

## Reviewing Papers
We walked through the papers in [[Related Papers]].

### Does the robot know what the groceries are before hand?
* Yes: If you order groceries, then you wknow whats in your order
* Yes: This simplifies our work.

### The Product Story:
There is a robot packing, and delivering the groccieres. Our Robot unpacks it and placese it in the fridge.

Unbox zone and a fridge zone.

Objects have catories based on where they go in the fridge.

## Preparing the Proposal
We discussed to what remaining work is needed to complete final project proposal.
Due Teusday

### Evaluation
* Idea: at the start - percent chance of successfully place object on a single run.
	* In simulation
* Idea:
	* Checkpoints:
		* % objects classified
		* % objects moved
		* % objects placemant zone determined
			* After blocked objects
* URarm - Robot in the lab. We can use it
	* Universal Robot Arm 3
	* https://www.universal-robots.com/products/ur3e/
* We will use simulation. Use GAZEBO.
* **Keven will make a README setup**

### Robot Planning
- Planning for arm movement
- Inverse kinomatics planning

### Topics
We will fill out the template with each of our topics.
Keven - manipulation
Alex - CV
Pascale - planning

https://www.overleaf.com/project/69bc515b46b38910ce249f37