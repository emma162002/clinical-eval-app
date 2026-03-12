FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Download real radiology images (public domain, Wikipedia Commons)
# If download fails (e.g. network), build continues; app will use SVG placeholders
RUN curl -f -L -o /app/static/ct_chest.jpg "https://upload.wikimedia.org/wikipedia/commons/3/3c/CT_of_lung_cancer_in_the_left_lung.jpg" \
    && curl -f -L -o /app/static/brain_mri.jpg "https://upload.wikimedia.org/wikipedia/commons/3/3c/MRI_brain_-_stroke_-_diffusion_weighted.jpg" \
    || true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

