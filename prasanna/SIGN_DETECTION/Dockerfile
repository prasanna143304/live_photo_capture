FROM python:3.9
RUN apt-get update && apt-get install -y libgl1-mesa-glx
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN python -OO -m py_compile thread.py && mv __pycache__/thread.cpython-39.opt-2.pyc thread.pyc && rm thread.py
CMD ["python", "sign_detection_orchestrator.py"]