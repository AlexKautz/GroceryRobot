# Summary

## What was discussed
* Project Story: "imagine a future where you receive a box of groceries from a delivery service (like Amazon), you take the box to your kitchen table and open it. Then your helpful robot arm takes items out of the box and places them in your refrigerator in their best position. We are programming that robot arm."
	* This story leads to the following considerations:
		* Our software already knows what is going to be in the box ahead of time, since it would've been specified in the grocery order.
		* We control what the box looks like, specifically we can print things on the bottom of the box that makes the computer vision tasks easier.
* For the scope and complexity of this project, we want to start small and simple and then expand as we get a feel for the amount of work it will take.
	* Starting with the groceries placed spaced apart in the box, then more close together, then stacked up upon one another.
	* Starting with easier to grab/recognize abstract objects, then more realistic objects.
* The entire project will be run in a simulation (GAZEBO). Usage of a physical robot can be follow up work.
	* Our simulated arm will be similar to the real robotic arm we have here in the robotics lab at Tufts. It is a [UR3e](https://www.universal-robots.com/products/ur3e/).
* The project can be broken up into these concepts:
	* Setting up the simulation itself
	* Running computer vision to identify the objects and their location
	* Running further computer vision to determine the best place to grab objects
	* Planning where each object goes in the refrigerator, taking into consideration
		* Different objects belong in different categories. Ice cream goes to the freezer, carrots go to the crisper drawer.
		* If an object is already in a location, we will need to put it next to that object. If we run out of space, we need to alert someone or choose the next best choice. (If there's no space for ice cream in the freezer, we need to tell someone. But it's OK to put carrots outside of the crisper drawer in the normal fridge if you need to.)
	* Motion planning (inverse kinematics) of the actual robotic arm as it grasps the object, moves it to where it needs to be, and places it.
* For evaluation, we decided to consider both evaluating the overall process and the parts of it.
	* Overall: during a full run, what percentage of the groceries got placed? What's the average over multiple runs?
	* Computer Vision: what percentage of objects get correctly identified?
	* Manipulation: given accurate object identification and a specified destination, what percentage of times can the arm successfully move the object without dropping it?
	* Planning: ...we didn't discuss this but we should think of a good planning metric...
* We are each focusing on the following topics. However they clearly overlap, so it's always good to communicate and read other people's work!
	* Alex
		* Computer vision
	* Kevin
		* Manipulation
	* Pascale
		* Planning
* For the **Project Proposal** due *Tuesday March 24th*:
	* We have a shared online Overleaf LaTeX document we can work on in parallel ([Link](https://www.overleaf.com/project/69bc515b46b38910ce249f37)).
	* We can each fill it out for our topic, and then meet to create the final document on Monday. See [[Team Meeting 3-23-2026]].
## Action Items
- [ ] **Alex:** Fill out the [project proposal](https://www.overleaf.com/project/69bc515b46b38910ce249f37) on the topic of computer vision. 📅 2026-03-23
- [ ] **Kevin:** Fill out the [project proposal](https://www.overleaf.com/project/69bc515b46b38910ce249f37) on the topic of manipulation. 📅 2026-03-23
- [ ] **Pascale:** Fill out the [project proposal](https://www.overleaf.com/project/69bc515b46b38910ce249f37) on the topic of planning. 📅 2026-03-23
- [ ] **Kevin:** Create a README about how to get the GAZEBO set up. (No due date)

- [ ] **All:** Follow up meeting: [[Team Meeting 3-23-2026]] to create our final project proposal document 📅 2026-03-23 ⏰ 11:00 AM

> [!note]- Raw Notes
> *these are the raw notes I took during the meeting. They are a mess but I'll keep them just in case there's something we need I forgot to add to the summary.*
> ## Members
> - Alex
> - Kevin
> - Pascale
> ## Project Idea:
> * Robot arm vs arm on a model platform
> * Bag of groceries vs a line up of groceries
> 	* Bag can lead to problems, but is more realistic
> 	* 3rd option, use a shallow box
> 		* "One robot brings the box, another opens it and gets the items"
> 		* Start simpler, where items are not ontop of each other, then move to a larger.
> 		* We controll the background/ bottom of the box
> 			* Place localization tags undernathe
> * A question of overall scope
> 	* Manipulation is the priority
> 	* How realistic is the setting?
> 		* represented grocerie items
> * We do not know where the objects are ahead of time
> 
> ### Semantic segmetation vs pointcloud segmentation
> * Where on a object do we grab.
> ### Grippers
> * Sole Grasping - Can only grasp
> * Suction Grasping
> * Multi-functinal grasper.
> ## Topics
> We reviewed the different topics we would focus on
> * Alex
> 	* Computer vision
> * Kevin
> 	* Manipulation
> * Pascale
> 	* Planning
> 	* Classification
> 
> ## Reviewing Papers
> We walked through the papers in [[Related Papers]].
> 
> ### Does the robot know what the groceries are before hand?
> * Yes: If you order groceries, then you wknow whats in your order
> * Yes: This simplifies our work.
> 
> ### The Product Story:
> There is a robot packing, and delivering the groccieres. Our Robot unpacks it and placese it in the fridge.
> 
> Unbox zone and a fridge zone.
> 
> Objects have catories based on where they go in the fridge.
> 
> ## Preparing the Proposal
> We discussed to what remaining work is needed to complete final project proposal.
> Due Teusday
> 
> ### Evaluation
> * Idea: at the start - percent chance of successfully place object on a single run.
> 	* In simulation
> * Idea:
> 	* Checkpoints:
> 		* % objects classified
> 		* % objects moved
> 		* % objects placemant zone determined
> 			* After blocked objects
> * URarm - Robot in the lab. We can use it
> 	* Universal Robot Arm 3
> 	* https://www.universal-robots.com/products/ur3e/
> * We will use simulation. Use GAZEBO.
> * **Kevin will make a README setup**
> 
> ### Robot Planning
> - Planning for arm movement
> - Inverse kinomatics planning
> 
> ### Topics
> We will fill out the template with each of our topics.
> Kevin - manipulation
> Alex - CV
> Pascale - planning
> 
> https://www.overleaf.com/project/69bc515b46b38910ce249f37