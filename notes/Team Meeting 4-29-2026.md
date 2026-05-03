* YOLO
	* We are getting the depth + square around the objects
	* Apple is detected as sports ball
	* We calculate the objects global location, converting from the camera frame.
* ROS
	* Move-It!
		* Added environment constraint for bannanna
		* Can move to fixed position (from YOLO)
			* Might need another translation
	* For other class
		* Real robot!
* Report
	* [Overleaf](https://www.overleaf.com/project/69efb0f4a3da6a34ba808193)
	* We have the template
	* The *Technical Approach / Methodology / Theoretical Framework* section has layeid out subsections and a "hook" to help with writing each one.
	* For the *Background* section we can combine the background section from our proposal and our notes on each of the documents we read
	* *Methodology, Experimental Results and Technical Demonstration* is the only part that is still up in the air. We need to start the experimenting before writing this section.
* Methodology ideas:
	* Colorsegmetation for categorization
	* Different shaped objets

* Next Steps:
	* V0
		* How do we get the objects from Gazeebo to Move-It!s internal representation?
			* this is necessary so the arm avoids hitting the side of the shelf or the top of the table when it is trying to move
			* We can harcode the objects (only the shelf and the table)
			* There might also be a way to import it automatically but that might not be worth the trouble
		* How does Move-It! treat objects it should pick up (the apple)?
			* these objects aren't things are trying to avoid, but certainly you need to be aware of their shape and size. We should research if there's a special way to treat them.
		* actually pull the Location from YOLO and have the robot arm moved to it with Move-It!
			* afterward extended to pick up the object and place it in a predestined place on the shelf. (we can hardcode this destination)
	* V1
		* lookup where to put the object in a table
		* run multiple simulations with the apple in different places
	* Methodology
		* Think of new ideas
Meeting next on Saturday, May 2 at 11 AM in the robotics lab
Till then:
	* Alex - busy with exam
	* Pascel - Work on the report ([Overleaf](https://www.overleaf.com/project/69efb0f4a3da6a34ba808193))
	* Keven - Look at the V0 next steps