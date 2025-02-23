# -*- coding: utf-8 -*-
"""project.ipynb

Automatically generated by Colab.

Original file is located at
	https://colab.research.google.com/drive/1K7v21oho6bkLGGm9fXiwG35X80FNMy4e

# Anomaly Detection in Cifar10

40 immagini deteriorate sono state aggiunte a una versione modificata del dataset cifar10.

TROVATELE!!

Istruzioni per scaricare il dataset sono date più in basso.
L'analisi deve fare riferimento solo al dataset fornito (non potete utilizzare in alcun modo Cifar10 originale).

## Cosa consegnare

Il risultato deve essere fornito sotto forma di **una lista di 40 indici** relativi agli outliers identificati.

Non potete restituire liste più lunghe. In tal caso, verrano troncate ai primi 40 elementi.

Il notebook deve spiegare la metodologia adottata e contenere le relative procedure. La metodologia deve essere automatica e non può prevedere nessuna supervisione umana.

## Dataset Downloading
"""

import numpy as np
import gdown

"""The following line should create in you local dicrectory a file named dataset.npy"""

# Use this line for Colab instead
#!gdown 1lccprYS7eWQBsLBsZS9J8qnETzRHBNZa
import os
if not os.path.exists('dataset.npy'):
	gdown.download('https://drive.google.com/uc?id=1lccprYS7eWQBsLBsZS9J8qnETzRHBNZa', 'dataset.npy', quiet=False)

dataset = np.load('dataset.npy',allow_pickle=True)

"""The dataset has shape (59900, 32, 32, 3)
No need to split it into train, validation and test.
"""

print(dataset.shape)

"""**IMPORTANTE**

Non riordinate il dataset caricato.
La lista di indici che restituite deve fare riferimento ad esso.


**Buon lavoro!!**

# Implementation

## Definitions

Import:
"""

import time
import matplotlib.pyplot as plt
from keras.models import Model
from keras.layers import Input, Conv2D, MaxPooling2D, UpSampling2D, BatchNormalization, Dropout
from keras.optimizers import Adam
from sklearn.metrics import mean_squared_error

"""
Initial definitions, e.g. for debugging and file usage:
"""


# True if running on Google Colab, False if in local
IN_COLAB = False

# True to allow loading saved weights
LOAD_WEIGHTS = True
# True to save plots/times to file
SAVE_PLOTS	= True
SAVE_TIMES	= True
SHOW_PLOTS	= False



if IN_COLAB:
	from google.colab import drive
	mount_path = '/content/drive'
	drive.mount(mount_path)
	save_path = mount_path +'/MyDrive/Colab Notebooks/res'
	PATH_WEIGHTS_CONV = f"{save_path}/weights_conv.weights.h5"
	PATH_TIMES = f"{save_path}/times.txt"
else:
	import os
	DIR_PLOTS = "images"
	DIR_WEIGHTS = "weights"
	PATH_WEIGHTS_CONV = f"{DIR_WEIGHTS}/weights_conv.weights.h5"
	PATH_TIMES = "times.txt"
	os.makedirs(DIR_PLOTS, exist_ok=True)
	os.makedirs(DIR_WEIGHTS, exist_ok=True)


PLOT_COUNTER	= 0
def PATH_PLOT(name):
	global PLOT_COUNTER
	PLOT_COUNTER += 1
	prefix = f"{save_path}/" if IN_COLAB else f"{DIR_PLOTS}/"
	return f"{prefix}plot_{name}_{PLOT_COUNTER - 1}.png"

def PATH_WEIGHTS(epochs_n: int, batch_size: int, filters: tuple[int,int], learning_rate: float):
	return f"{PATH_WEIGHTS_CONV.split('.weights.h5')[0]}_{epochs_n}_{batch_size}_{filters[0]}_{filters[1]}_{LEARNING_RATE}.weights.h5"


"""
Functions for plots:
"""

def img_show(img):
	plt.imshow(img, cmap="gray")
	plt.show()

def plot_images_horizontally(images, num_images, cmap='gray', name='horizontal'):
	plt.figure(figsize=(20, 20))
	for i in range(num_images):
		plt.subplot(1, num_images, i+1)
		plt.imshow(images[i], cmap=cmap)
		plt.axis('off')
	if SAVE_PLOTS:
		plt.savefig( PATH_PLOT(name) )
	if SHOW_PLOTS:
		plt.show()

def plot_images(images, figsize, cmap='gray', name='grid'):
	scaler = 10
	plt.figure(figsize=(figsize[0]*scaler, figsize[1]*scaler))
	for i in range(min(figsize[0]*figsize[1], len(images))):
		plt.subplot(figsize[0], figsize[1], i+1)
		plt.imshow(images[i], cmap=cmap)
		plt.axis('off')
	if SAVE_PLOTS:
		plt.savefig( PATH_PLOT(name) )
	if SHOW_PLOTS:
		plt.show()

def plot_hist(data, label_x, label_y, title, bins=50, log_scale=True, name='hist'):
	plt.figure(figsize=(12, 4))
	plt.hist(data, bins=bins)
	if log_scale:
		plt.yscale('log')
	plt.xlabel(label_x)
	plt.ylabel(label_y)
	plt.title(title)
	if SAVE_PLOTS:
		plt.savefig( PATH_PLOT(name) )
	if SHOW_PLOTS:
		plt.show()

def plot_hist_err_reconstruction(data, bins=50, log_scale=True, name='hist'):
	plot_hist(data, 'Reconstruction error', 'No of examples', 'Distribution of reconstruction errors', bins=bins, log_scale=log_scale, name=name)

def plot_scatter(x, y, label, label_x, label_y, name='scatter'):
	plt.figure(figsize=(12, 4))
	plt.scatter(x, y, label=label)
	plt.legend()
	plt.xlabel(label_x)
	plt.ylabel(label_y)
	if SAVE_PLOTS:
		plt.savefig( PATH_PLOT(name) )
	if SHOW_PLOTS:
		plt.show()

def plot_scatter_err_reconstruction(errors, name='scatter'):
	indices = range(len(errors))
	plot_scatter(indices, errors, 'Reconstruction error', 'Index', 'Reconstruction error', name=name)


def plot_training_history(history, num_epochs, name='history'):

	training_loss = history.history['loss']
	training_metrics = history.history['accuracy']

	epochs = range(1, num_epochs + 1)
	plt.figure(figsize=(12, 4))

	plt.subplot(1, 2, 1)
	plt.plot(epochs, training_loss, label='Training Loss')
	plt.title('Loss')
	plt.xlabel('Epochs')
	plt.legend()

	plt.subplot(1, 2, 2)
	plt.plot(epochs, training_metrics, label='Training Accuracy')
	plt.title('Accuracy')
	plt.xlabel('Epochs')
	plt.legend()

	plt.tight_layout()
	if SAVE_PLOTS:
		plt.savefig( PATH_PLOT(name) )
	if SHOW_PLOTS:
		plt.show()



"""
## MODEL

Model definition: autoencoder with convolutional layers:
"""

# hypermarameters
BATCH_SIZE	= 256
FILTERS	= (32,64)
LEARNING_RATE = 0.0005
N_EPOCHS = 100
CONV_KERNEL_SIZE = (3,3)
CONV_STRIDE = (1,1)
MAX_POOLING_KERNEL_SIZE = (2,2)
MAX_POOLING_STRIDE = None	# default to pool_size
UPSAMPLING_SIZE = (2,2)

optimizer = Adam(learning_rate=LEARNING_RATE)


# For output files
path_weights = PATH_WEIGHTS(N_EPOCHS, BATCH_SIZE, FILTERS, LEARNING_RATE)
plot_params = f"{N_EPOCHS}_{BATCH_SIZE}_{FILTERS[0]}_{FILTERS[1]}_{LEARNING_RATE}"


# normalize dataset
ds_preprocessed = dataset / 255.0


# Define the convolutional autoencoder
input_img = Input(shape=(32, 32, 3), name="input")

# Encoder
x = Conv2D(FILTERS[0], CONV_KERNEL_SIZE, CONV_STRIDE, activation='relu', padding='same', name='encoded_conv2d_1')(input_img)
x = MaxPooling2D(MAX_POOLING_KERNEL_SIZE, MAX_POOLING_STRIDE, padding='same', name='encoded_maxPooling2d_1')(x)
x = Conv2D(FILTERS[1], CONV_KERNEL_SIZE, CONV_STRIDE, activation='relu', padding='same', name='encoded_conv2d_2')(x)
encoded = MaxPooling2D(MAX_POOLING_KERNEL_SIZE, MAX_POOLING_STRIDE, padding='same', name='encoded_maxPooling2d_2')(x)

# Decoder
x = Conv2D(FILTERS[1], CONV_KERNEL_SIZE, CONV_STRIDE, activation='relu', padding='same', name='decoded_conv2d_1')(encoded)
x = UpSampling2D(UPSAMPLING_SIZE, name='decoded_upSampling2d_1')(x)
x = Conv2D(FILTERS[0], CONV_KERNEL_SIZE, CONV_STRIDE, activation='relu', padding='same', name='decoded_conv2d_2')(x)
x = UpSampling2D(UPSAMPLING_SIZE, name='decoded_upSampling2d_2')(x)
decoded = Conv2D(3, CONV_KERNEL_SIZE, CONV_STRIDE, activation='sigmoid', padding='same', name='decoded_conv2d_3')(x)

autoencoder = Model(input_img, decoded)
autoencoder.summary()
autoencoder.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy'])

"""
Train:
"""

try:
	if LOAD_WEIGHTS:
		autoencoder.load_weights(path_weights)
		print("Loaded weights for CONVOLUTIONAL")
	else:
		raise Exception
except Exception as e:
	print(f"Loading CONVOLUTIONAL Error: {e}")
	print("Didn't load weights, training CONVOLUTIONAL")

	time_start = time.time()
	history = autoencoder.fit(ds_preprocessed, ds_preprocessed, epochs=N_EPOCHS, batch_size=BATCH_SIZE, shuffle=True)
	time_end = time.time()
	if(SAVE_TIMES):
		with open(PATH_TIMES, "a") as f:
			f.write(f"conv\t{N_EPOCHS}\t{BATCH_SIZE}\t{FILTERS}\t{LEARNING_RATE}\t: {time_end - time_start}s\n")
	print(f"Training time: {time_end - time_start} seconds")  # Print the time taken by the fit function
	
	if LOAD_WEIGHTS:
		autoencoder.save_weights(path_weights)
	print("Training done, weights saved")
	plot_training_history(history, N_EPOCHS, name=f"conv{plot_params}_history")


"""
Execute and find anomalies, as the 40 images with highest error 
(mean squared error, applied on the images reconstructed by the autoencoder and flattened):
"""

# Use the autoencoder to reconstruct the dataset
ds_reconstructed = autoencoder.predict(ds_preprocessed)

# Flatten the original and reconstructed datasets for comparison
ds_flat = ds_preprocessed.reshape(ds_preprocessed.shape[0], -1)
ds_reconstructed_flat = ds_reconstructed.reshape(ds_reconstructed.shape[0], -1)

# Calculate the reconstruction error for each image
error_reconstruction = np.array([mean_squared_error(ds_flat[i], ds_reconstructed_flat[i]) for i in range(ds_flat.shape[0])])

# Plots
error_reconstruction_flat = error_reconstruction.flatten()
plot_hist_err_reconstruction(error_reconstruction_flat, name=f"conv{plot_params}_hist")
plot_scatter_err_reconstruction(error_reconstruction, name=f"conv{plot_params}_scatter")

# Identify the 40 images with the highest reconstruction error as anomalies
anomalies = error_reconstruction.argsort()[-40:]

"""
Print and plot the found anomalies (sorted):
"""

# Print anomalies
anomalies = sorted(anomalies)
print(anomalies)
anomalies_img = []
for i in anomalies:
	anomalies_img.append(dataset[i])
plot_images(anomalies_img, (8,5), name=f"conv{plot_params}")



"""

## Commenti

Si è scelto di usare un autoencoder essendo uno dei metodi principali per clustering e anomaly detection, in particolare su dati più complessi come delle immagini: sono stati provati sommariamente anche altri modelli, ma autoencoder con semplici strati densi non danno risultati ottimali, non essendo forse non essendo adatti a lavorare su immagini, e in particolare gli algoritmi di clustering (dbScan, K-Means, Isolation Forest, One-Class SVM, LOF, elliptic) non sembrano proprio riuscire a distinguere le anomalie.

Le immagini identificate come anomalie fanno ben sperare, poiché sembrano tutte ricoperte da un'interferenza o uno "scarabocchio".  
In più, come si può osservare soprattutto dal grafico scatter, ci sono esattamente 40 immagini che spiccano su tutto il dataset per un maggiore errore di ricostruzione. In realtà ci sono anche altri punti del grafico che sembrano avvicinarcisi, ma dopo aver provato un po' di combinazioni diverse di iperparametri, con gli attuali sembra che l'insieme dei primi 40 sia più staccato dal resto: infatti, con altri iperparametri alcune delle attuali anomalie identificate veniva scambiata con qualche altra con un errore, in quel caso, maggiore (c'è un'altra immagine in particolare che riporta sempre un errore di ricostruzione molto più vicino alle altre anomalie che alla maggioranza, e che ha avuto più difficoltà a distanziarsi da esse).  
Anche le curve di loss e accuracy risultavano meno regolari con altri iperparametri, o costanti, o con un improvviso scatto iniziale, indicando forse un apprendimento troppo rapido.
Altre combinazioni di parametri producono risultati quasi equivalenti, ma gli attuali sembrano leggermente migliori per le caretteristiche appena citate: per esempio, darebbe risultati simili raddoppiare il learning rate a 0.001 e dimezzare le epoch a 50, ma il grafico di training sarebbe un po' meno regolare.

### Altri tentativi

Altri tentativi, con training meno regolare o minore distinzione delle anomalie (sbagliando, a volte, a riconoscerne alcune):
* batch size: più bassa (64,128) ha una history irregolare, essendo forse più soggetta alle anomalie o piccole variazioni; più alta (384) apprende troppo velocemente (e inizia a richiedere troppa memoria);
* meno filtri (16) migliorano meno loss e accuracy;
* filtri (32,32), (64,64) hanno risultati simili, ma gli attuali sono leggermente migliori per separazione delle anomalie;
* più filtri (128,128 o 64,128), pur avendo una maggiore accuracy/minore loss e riuscendo comunque a riconoscere le stesse anomalie, le separano leggermente meno rispetto ai filtri attuali, e hanno un grafico meno stabile;
* altri strati (dropout, batchNormalization) sembrano peggiorare accuracy e velocità di addestramento e non riconoscono le stesse anomalie delle attuali;
* con meno epoch i risultati ancora non sono ottimali, e di più aumentano di poco l'accuracy ma distinguono peggio le 40 anomalie di questo specifico caso.

"""
