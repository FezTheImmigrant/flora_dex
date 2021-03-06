#!/usr/bin/python3
import pandas as pd
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty 
from interactable_page import InteractablePage
from threading import Timer
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from PIL import Image
import numpy as np
from threading import Thread

import numpy as np
import tflite_runtime.interpreter as tflite

class Picture(GridLayout,InteractablePage):

    capture_button = ObjectProperty(None)
    camera = ObjectProperty(None)
    captured_label = ObjectProperty(None)

    def __init__(self,keyboard, **kwargs):
        super(Picture,self).__init__(**kwargs)

        self.button_list = [self.capture_button]

        self._keyboard = keyboard 
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

        self.df = pd.read_csv("/home/pi/dev/flora_dex/application/raw_data/image_paths.csv")

        ## get all unique labels and sort them (for classification_report)
        self.classes = list(self.df['label'].unique())
        self.classes.sort()

        self.interpreter = tflite.Interpreter(model_path='model.tflite')
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        self.data_gen =ImageDataGenerator(
            samplewise_center = True,
            samplewise_std_normalization = True,
            rescale=1.0/255.0,
        )


    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):

        # double press on gamepad for whatever reason
        if (not self.ignore_next and self.has_focus):
            if (keycode[1] == 'right' or keycode[1] == 'down'):
                self.set_button_index(True)
            elif (keycode[1] == 'left' or keycode[1] == 'up'):
                self.set_button_index(False)
            elif (keycode[1] == 'lctrl'):
                self.select()

        self.ignore_next = not self.ignore_next

    def add_picture_callback(self,picture_callback):
        self.picture_callback = picture_callback

    def process_capture(self):


        camera = self.ids['camera']
        camera.export_to_png("/home/pi/dev/flora_dex/application/capture.png")


        t = Thread(target=self.capture_thread)
        t.start() 
        t.join() 

        self.captured_label.opacity = 1.0
        timer = Timer(3.0, self.captured_timer)
        timer.start()

    def captured_timer(self):
        self.captured_label.opacity = 0.0

    def capture_thread(self):

        rgba = Image.open('/home/pi/dev/flora_dex/application/capture.png')
        rgba.load() # required for png.split()

        # need to get rid of alpha channel
        image = Image.new("RGB", rgba.size, (255, 255, 255))
        image.paste(rgba, mask=rgba.split()[3]) # 3 is the alpha channel

        image = image.resize((256,256))

        image = np.asarray(image,dtype=np.float32)
        image = image.reshape(1, 256, 256, 3)

        # post process image
        self.data_gen.standardize(image)

        # run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], image)
        self.interpreter.invoke()
        prediction = self.interpreter.get_tensor(self.output_details[0]['index'])
        prediction = prediction.flatten()

        max_five = prediction.argsort()[-5:][::-1].tolist()
        max_five_classes = [self.classes[i] for i in max_five]
        print(max_five_classes)

        self.picture_callback(max_five_classes,[prediction[i] for i in max_five])

    def select(self):
        if (self.current_button.text == "Capture"):
            self.process_capture()