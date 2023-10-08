FROM python:3.8

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libx264-dev \
    yasm \
    libvpx-dev \
    libavcodec-dev \
    libavformat-dev \
    libmp3lame-dev \
    libopus-dev \
    python3-opencv \
    imagemagick

RUN cd /usr/src && \
    wget http://www.ffmpeg.org/releases/ffmpeg-4.2.2.tar.bz2 && \
    tar xjvf ffmpeg-4.2.2.tar.bz2 && \
    cd ffmpeg-4.2.2 && \
    ./configure --enable-gpl --enable-libx264 && \
    make && \
    make install

RUN pip install Django Flask Pyramid Tornado Requests Beautifulsoup4 selenium Scrapy numpy pandas matplotlib scikit-learn keras nltk gensim numpy requests pillow imageio seaborn moviepy pandas scikit-image plotly opencv-python

RUN mkdir /data

CMD ["python3"]
