Home Assistant Lightmap
=================================================================================
Lightmap is a Home Assistant integration designed to help visualize light levels within a living space. It incorporates an SVG floorplan into a custom panel, allowing users to easily place virtual sensors on the floorplan to represent the physical light-measuring sensors deployed throughout the space.

This tool provides an intuitive way to analyze light distribution in your environment, making it especially useful for tasks such as determining optimal plant placement based on specific light requirements.

Getting Started with Lightmap
=============================

The first step in using **Lightmap** is to create an SVG floorplan. We recommend using `Inkscape <https://inkscape.org>`_, a free and user-friendly tool for creating and editing SVG files.

Steps to Create Your Floorplan
------------------------------

1. **Create a Background (Optional)**

   - Add a new layer to your SVG and name it **"Background"**.
   - Import an image of your floorplan that represents your living space into this layer.
   - While optional, adding a background makes the visualization more appealing and simplifies the process of defining rooms.

2. **Define Rooms**

   - Add a new layer to your SVG and name it **"rooms"**.
   - Within the **"rooms"** layer, create a separate sub-layer for each room and name them accordingly (e.g., **"LivingRoom"**, **"Bedroom"**, etc.).
   - Use the rectangle tool to draw the internal space of each room on the canvas. Assign each rectangle to the corresponding room layer.
   - Set the opacity of each rectangle to ``0`` to make them invisible while still maintaining their functionality for mapping sensor data.

3. **Save file**

   - Now that the background and rooms have been defined, the svg can be saved. Save the svg as a **plain svg** with a name of your choice.  

Steps to Upload the SVG and Add Sensors
---------------------------------------

1. **Upload Your Floorplan**

   - Open Home Assistant and navigate to the **Lightmap** panel by clicking it in the sidebar on the left.
   - To upload your floorplan file, click the **Upload** button and select the SVG file you created. The floorplan should now be visible within the panel.

2. **Add Sensors to the Floorplan**

   - To add sensors to the floorplan, ensure that the sensors are set up in Home Assistant beforehand.
   - Once the sensors have been added to Home Assistant, they will appear as a list on the right side of the uploaded floorplan.
   - Select a sensor from the list, then click on the desired location on the floorplan. This will map the selected sensor to the corresponding location.
   - **Note:** Sensors must be placed within a defined room. If a sensor is placed outside any room, the visual light representation will not display correctly.
   - Once readings from the placed sensors are sent to Home Assistant, the floorplan will automatically update to reflect the sensor data.

Using the plant placement assistant 
---------------------------------------

- Open the assistant by clicking on the icon in the bottom right of the panel. Once opened, a plant name can be entered into the text field. The AI assistant will then determine the light requirements of the given plant and our system will link that light requirement with the available sensors, which will be displayed in the chat box. If none of the current sensors match the light requirements, only the recommended light requirement will be displayed.
