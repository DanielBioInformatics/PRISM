FROM continuumio/miniconda3:23.10.0-1

RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY environment.yml .
RUN conda env create -f environment.yml && \
    conda clean --all -y

SHELL ["conda", "run", "-n", "prism", "/bin/bash", "-c"]

COPY . .

EXPOSE 5000

CMD ["conda", "run", "-n", "prism", "python", "app.py"]
