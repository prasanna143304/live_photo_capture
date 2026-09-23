FROM python:3.9
WORKDIR /app
COPY . .
RUN apt-get update && \
    apt-get install -y build-essential cmake ffmpeg && \
    pip install -r requirements.txt

RUN python -OO -m py_compile thread.py && mv __pycache__/thread.cpython-39.opt-2.pyc thread.pyc && rm thread.py
CMD ["python", "blink_detection_orchestrator.py"]