import tensorflow as tf
import numpy as np
from Unet import UNet
from discriminator import Discriminator
import os
from PIL import Image
import random
import time 

class Train():
    def __init__(self):

        #realA RGB
        self.realA = tf.placeholder(tf.float32, shape=[None,388,388,3])
        
        #realB 線画
        self.reshaped_realB = tf.placeholder(tf.float32, shape=[None,388,388,3])
        self.realB = tf.placeholder(tf.float32, shape=[None,572,572,3])

        #batch_size
        batch_size = self.realA.get_shape().as_list()[0]
        
        #Generated by UNet used realB
        #fakeA 着色
        self.fakeA = UNet(self.realB).dec_conv_last

        #concat
        #positive
        #realAB
        realAB = tf.concat([self.realA, self.reshaped_realB], 3)        
        #negative
        #fakeAB
        fakeAB = tf.concat([self.fakeA, self.reshaped_realB], 3)
        
        #discriminator
        dis_real = Discriminator(realAB, batch_size)
        real_logits = dis_real.last_h
        real_out = dis_real.out

        dis_fake = Discriminator(fakeAB, batch_size)
        fake_logits = dis_fake.last_h
        fake_out = dis_fake.out

        self.d_loss_real = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=real_logits, labels=tf.ones_like(real_out)))
        self.d_loss_fake = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=fake_logits, labels=tf.zeros_like(fake_out)))
        self.UNet_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=fake_logits, labels=tf.ones_like(fake_out)))

        self.d_loss = self.d_loss_fake + self.d_loss_real
        self.g_loss = self.UNet_loss + 100*tf.reduce_mean(tf.abs(self.realA-self.fakeA))
        self.opt_d = tf.train.AdamOptimizer(0.0003).minimize(self.d_loss)
        self.opt_g = tf.train.AdamOptimizer(0.0003).minimize(self.g_loss)


batch_size = 2
epochs = 3000
filenames = os.listdir('./data/rgb388/')
data_size = len(filenames)
step = int(data_size/batch_size)

if not os.path.exists('./saved/'):
    os.mkdir('./saved/')

if not os.path.exists('./visualized/'):
    os.mkdir('./visualized/')

def sample(size, channel, path, batch_files):
    imgs = np.empty((0,size,size,channel), int)

    for file_name in batch_files:
        img = np.array(Image.open(path+file_name))
        #print(imgs.shape,img.shape) 
        imgs = np.append(imgs, np.array([img]), axis=0)
    imgs = imgs.reshape((-1,size,size,channel))
    return imgs

#batch_files = [random.choice(filenames) for _ in range(batch_size)]  
#sample(size=388, channel=3, path='./data/linedraw388/', batch_files=batch_files)

def visualize_g(size, g_img, t_img, batch_size, epoch, i):
    for n in range(batch_size):
        img = np.concatenate((g_img[n],t_img[n]),axis=1)
        img = Image.fromarray(np.uint8(img))
        img.save('./visualized/epoch{}batch_num{}batch{}.jpg'.format(epoch,n,i))
    

train = Train()
with tf.Session(config=tf.ConfigProto(allow_soft_placement=True, log_device_placement=True)) as sess:
    tf.global_variables_initializer().run()
    saver = tf.train.Saver(tf.global_variables())
    
    for epoch in range(epochs):
        new_time = time.time() 
        for i in range(0, data_size, batch_size):
            batch_files = [random.choice(filenames) for _ in range(batch_size)]
            
            rgb388 = sample(388, 3, './data/rgb388/', batch_files)
            linedraw388 = sample(388, 3, './data/linedraw388/', batch_files)
            linedraw572 = sample(572, 3, './data/linedraw572/', batch_files)
            
            batch_time = time.time()
            d_loss, _ = sess.run([train.d_loss,train.opt_d],{train.realA:rgb388,train.reshaped_realB:linedraw388,train.realB:linedraw572})
            g_img, g_loss, _ = sess.run([train.fakeA,train.g_loss,train.opt_g],{train.realA:rgb388,train.reshaped_realB:linedraw388,train.realB:linedraw572})
             
            visualize_g(388, g_img, linedraw388, batch_size, epoch, i)
            print('    g_loss:',g_loss,'    d_loss:',d_loss,' speed:',time.time()-batch_time," batches / s")

        print('--------------------------------')
        print('epoch_num:',epoch,'    epoch_time:',time.time()-new_time)
        print('--------------------------------')
        saver.save(sess, "saved/model.ckpt")
