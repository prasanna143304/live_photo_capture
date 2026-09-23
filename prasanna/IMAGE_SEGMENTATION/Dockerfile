FROM python:3.9
RUN apt-get update && apt-get install -y libgl1-mesa-glx
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN sed -i 's/from tensorflow.python.keras.layers import BatchNormalization/from tensorflow.keras.layers import BatchNormalization/' /usr/local/lib/python3.9/site-packages/pixellib/semantic/deeplab.py
RUN python -OO -m py_compile thread.py && mv __pycache__/thread.cpython-39.opt-2.pyc thread.pyc && rm thread.py
CMD ["python", "image_segmentation_orchestrator.py"]