'''
This code is due to Yutong Deng (@yutongD), Yingtong Dou (@YingtongDou) and UIC BDSC Lab
DGFraud (A Deep Graph-based Toolbox for Fraud Detection)
https://github.com/safe-graph/DGFraud

GAS ('Spam Review Detection with Graph Convolutional Networks')
Parameters:
    nodes: total nodes number
    class_size: class number
    embedding_i: item embedding size
    embedding_u: user embedding size
    embedding_r: review embedding size
    gcn_dim: the gcn layer unit number
'''
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../..')))
import tensorflow as tf
from base_models.models import GCN
from base_models.layers import AttentionLayer, ConcatenationAggregator, AttentionAggregator, GASConcatenation
from algorithms.base_algorithm import Algorithm


class GAS(Algorithm):
    def __init__(self, session, nodes, class_size, embedding_i, embedding_u, embedding_r, h_u_size, h_i_size,
                 encoding1, encoding2, encoding3, encoding4, gcn_dim, meta=1, concat=True, **kwargs):
        super().__init__(**kwargs)
        self.meta = meta
        self.nodes = nodes
        self.class_size = class_size
        self.embedding_i = embedding_i
        self.embedding_u = embedding_u
        self.embedding_r = embedding_r
        self.encoding1 = encoding1
        self.encoding2 = encoding2
        self.encoding3 = encoding3
        self.encoding4 = encoding4
        self.gcn_dim = gcn_dim
        self.h_i_size = h_i_size
        self.h_u_size = h_u_size
        self.concat = concat
        self.build_placeholders()
        self.train_op = None

        loss, probabilities = self.forward_propagation()
        self.loss, self.probabilities = loss, probabilities
        #self.l2 = tf.contrib.layers.apply_regularization(tf.contrib.layers.l2_regularizer(0.01),
        #                                                         tf.trainable_variables())
        self.l2 = tf.keras.regularizers.l2(0.01)
        #loss = loss + self.l2(W)

        self.pred = tf.one_hot(tf.argmax(self.probabilities, 1), class_size)
        print(self.pred.shape)
        self.correct_prediction = tf.equal(tf.argmax(self.probabilities, 1), tf.argmax(self.t, 1))
        self.accuracy = tf.reduce_mean(tf.cast(self.correct_prediction, "float"))
        print('Forward propagation finished.')

        self.sess = session
        #self.optimizer = tf.train.AdamOptimizer(self.lr)
        #self.optimizer = tf.keras.optimizers.Adam(self.lr)

        initial_learning_rate = 0.1
        lr_schedule = tf.keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate,
            decay_steps=100000,
            decay_rate=0.96,
            staircase=True)

        self.optimizer = tf.keras.optimizers.Adam(learning_rate=lr_schedule)

        #gradients = self.optimizer.compute_gradients(self.loss + self.l2)
        #capped_gradients = [(tf.clip_by_value(grad, -5., 5.), var) for grad, var in gradients if grad is not None]
        #self.train_op = self.optimizer.apply_gradients(capped_gradients)

        #self.trainable_variables = [var for var in tf.trainable_variables() if 'GAS' in var.name]

        W = tf.Variable(initial_value=tf.initializers.GlorotUniform()([self.encoding1 + 2 * self.encoding2 + 2 * self.nodes + self.nodes,
                                                                self.class_size]), name='weights')
        b = tf.Variable(initial_value=tf.zeros([1, self.class_size]), name='bias')

        self.trainable_variables = [W,b]

        with tf.GradientTape() as tape:
            reg_loss = self.l2(self.loss)
            total_loss = self.loss + reg_loss
        gradients = tape.gradient(total_loss, self.trainable_variables)
        non_none_gradients = [grad_var for grad_var in zip(gradients, self.trainable_variables) if grad_var[0] is not None]

        if non_none_gradients:  # Check if the list is not empty
            capped_gradients = [(tf.clip_by_value(grad, -5., 5.), var) for grad, var in non_none_gradients]
            self.train_op = self.optimizer.apply_gradients(capped_gradients)
        else:
            print("Warning: all gradients are None. Check the definition of loss and trainable variables.")

        #self.init = tf.global_variables_initializer() #not needed in TF 2
        print('Backward propagation finished.')

    def build_placeholders(self):
        # self.user_review_adj = tf.placeholder(tf.float32, [None, None], 'adjlist1')
        # self.user_item_adj = tf.placeholder(tf.float32, [None, None], 'adjlist2')
        # self.item_review_adj = tf.placeholder(tf.float32, [None, None], 'adjlist3')
        # self.item_user_adj = tf.placeholder(tf.float32, [None, None], 'adjlist4')
        # self.review_user_adj = tf.placeholder(tf.float32, [None], 'adjlist5')
        # self.review_item_adj = tf.placeholder(tf.float32, [None], 'adjlist6')
        # self.homo_adj = tf.placeholder(tf.float32, [self.nodes, self.nodes], 'comment_adj')
        # self.review_vecs = tf.placeholder(tf.float32, [None, None], 'init_embedding1')
        # self.user_vecs = tf.placeholder(tf.float32, [None, None], 'init_embedding2')
        # self.item_vecs = tf.placeholder(tf.float32, [None, None], 'init_embedding3')
        # self.batch_index = tf.placeholder(tf.int32, [None], 'index')
        # self.t = tf.placeholder(tf.float32, [None, self.class_size], 'labels')
        # self.lr = tf.placeholder(tf.float32, [], 'learning_rate')
        # self.mom = tf.placeholder(tf.float32, [], 'momentum')
        self.user_review_adj = tf.compat.v1.placeholder(tf.float32, [None, None], 'adjlist1')
        self.user_item_adj = tf.compat.v1.placeholder(tf.float32, [None, None], 'adjlist2')
        self.item_review_adj = tf.compat.v1.placeholder(tf.float32, [None, None], 'adjlist3')
        self.item_user_adj = tf.compat.v1.placeholder(tf.float32, [None, None], 'adjlist4')
        self.review_user_adj = tf.compat.v1.placeholder(tf.float32, [None], 'adjlist5')
        self.review_item_adj = tf.compat.v1.placeholder(tf.float32, [None], 'adjlist6')
        self.homo_adj = tf.compat.v1.placeholder(tf.float32, [self.nodes, self.nodes], 'comment_adj')
        self.review_vecs = tf.compat.v1.placeholder(tf.float32, [None, None], 'init_embedding1')
        self.user_vecs = tf.compat.v1.placeholder(tf.float32, [None, None], 'init_embedding2')
        self.item_vecs = tf.compat.v1.placeholder(tf.float32, [None, None], 'init_embedding3')
        self.batch_index = tf.compat.v1.placeholder(tf.int32, [None], 'index')
        self.t = tf.compat.v1.placeholder(tf.float32, [None, self.class_size], 'labels')
        self.lr = tf.compat.v1.placeholder(tf.float32, [], 'learning_rate')
        self.mom = tf.compat.v1.placeholder(tf.float32, [], 'momentum')

    def forward_propagation(self):
        with tf.compat.v1.variable_scope('hete_gcn'):
        #with tf.variable_scope('hete_gcn'):
            r_aggregator = ConcatenationAggregator(input_dim=self.embedding_r + self.embedding_u + self.embedding_i,
                                                   output_dim=self.encoding1,
                                                   review_item_adj=self.review_item_adj,
                                                   review_user_adj=self.review_user_adj,
                                                   review_vecs=self.review_vecs, user_vecs=self.user_vecs,
                                                   item_vecs=self.item_vecs)
            h_r = r_aggregator(inputs=None)

            iu_aggregator = AttentionAggregator(input_dim1=self.h_u_size, input_dim2=self.h_i_size,
                                                output_dim=self.encoding3, hid_dim=self.encoding2, user_review_adj=self.user_review_adj,
                                                user_item_adj=self.user_item_adj,
                                                item_review_adj=self.item_review_adj, item_user_adj=self.item_user_adj,
                                                review_vecs=self.review_vecs, user_vecs=self.user_vecs,
                                                item_vecs=self.item_vecs, concat=True)
            h_u, h_i = iu_aggregator(inputs=None)
            print('Nodes embedding over!')

        with tf.compat.v1.variable_scope('homo_gcn'):
        #with tf.variable_scope('homo_gcn'):
            x = self.review_vecs
            # gcn_out = GCN(x, self.homo_adj, self.gcn_dim, self.embedding_r,
            #               self.encoding4).embedding()
        print('Comment graph embedding over!')

        with tf.compat.v1.variable_scope('classification'):
        #with tf.variable_scope('classification'):
            concatenator = GASConcatenation(review_user_adj=self.review_user_adj, review_item_adj=self.review_item_adj,
                                            review_vecs=h_r, homo_vecs=self.homo_adj,
                                            user_vecs=h_u, item_vecs=h_i)
            concated_hr = concatenator(inputs=None)

            batch_data = tf.matmul(tf.one_hot(self.batch_index, self.nodes), concated_hr)
            # W = tf.get_variable(name='weights',
            #                     shape=[self.encoding1 + 2 * self.encoding2 + 2 * self.nodes + self.nodes,
            #                            self.class_size],
            #                     initializer=tf.contrib.layers.xavier_initializer())
            # W = tf.Variable(name='weights',
            #                     shape=[self.encoding1 + 2 * self.encoding2 + 2 * self.nodes + self.nodes,
            #                            self.class_size],
            #                     initializer=tf.contrib.layers.xavier_initializer())
            # W = tf.Variable(name='weights',
            #     shape=[self.encoding1 + 2 * self.encoding2 + 2 * self.nodes + self.nodes,
            #            self.class_size],
            #     initializer=tf.initializers.GlorotUniform())
            W = tf.Variable(initial_value=tf.initializers.GlorotUniform()([self.encoding1 + 2 * self.encoding2 + 2 * self.nodes + self.nodes,
                                                               self.class_size]), name='weights')
            
            #b = tf.get_variable(name='bias', shape=[1, self.class_size], initializer=tf.zeros_initializer())
            #b = tf.Variable(name='bias', shape=[1, self.class_size], initializer=tf.zeros_initializer())
            #b = tf.Variable(name='bias', shape=[1, self.class_size], initializer=tf.zeros_initializer())
            b = tf.Variable(initial_value=tf.zeros([1, self.class_size]), name='bias')

            tf.transpose(batch_data, perm=[0, 1])
            logits = tf.matmul(batch_data, W) + b
            #loss = tf.losses.sigmoid_cross_entropy(multi_class_labels=self.t, logits=logits)
            loss_fn = tf.keras.losses.BinaryCrossentropy(from_logits=True)
            loss = loss_fn(self.t, logits)

        return loss, tf.nn.sigmoid(logits)

    def train(self, h, adj_info, t, b, learning_rate=1e-2, momentum=0.9):
        feed_dict = {
            self.user_review_adj: adj_info[0],
            self.user_item_adj: adj_info[1],
            self.item_review_adj: adj_info[2],
            self.item_user_adj: adj_info[3],
            self.review_user_adj: adj_info[4],
            self.review_item_adj: adj_info[5],
            self.homo_adj: adj_info[6],
            self.review_vecs: h[0],
            self.user_vecs: h[1],
            self.item_vecs: h[2],
            self.t: t,
            self.batch_index: b,
            self.lr: learning_rate,
            self.mom: momentum
        }

        initial_learning_rate = 0.1
        lr_schedule = tf.keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate,
            decay_steps=100000,
            decay_rate=0.96,
            staircase=True)

        # Define your optimizer
        optimizer = tf.keras.optimizers.Adam(learning_rate=lr_schedule)

        # Define your training operation
        with tf.GradientTape() as tape:
            #logits = self.model(feed_dict)  # Replace with your actual function to compute the logits
            logits = self.graph_convolutional_layers(feed_dict)
            loss = loss_fn(self.t, logits)
        gradients = tape.gradient(loss, self.trainable_variables)  # Replace with your actual trainable variables
        self.train_op = optimizer.apply_gradients(zip(gradients, self.trainable_variables))

        #outs = self.sess.run(
        #    [self.train_op, self.loss, self.accuracy, self.pred, self.probabilities],
        #    feed_dict=feed_dict)
        outs = self.sess.run([self.train_op, self.loss, self.accuracy, self.pred, self.probabilities], feed_dict=feed_dict)

        loss = outs[1]
        acc = outs[2]
        pred = outs[3]
        prob = outs[4]
        return loss, acc, pred, prob

    def test(self, h, adj_info, t, b):
        feed_dict = {
            self.user_review_adj: adj_info[0],
            self.user_item_adj: adj_info[1],
            self.item_review_adj: adj_info[2],
            self.item_user_adj: adj_info[3],
            self.review_user_adj: adj_info[4],
            self.review_item_adj: adj_info[5],
            self.homo_adj: adj_info[6],
            self.review_vecs: h[0],
            self.user_vecs: h[1],
            self.item_vecs: h[2],
            self.t: t,
            self.batch_index: b
        }
        acc, pred, probabilities, tags = self.sess.run(
            [self.accuracy, self.pred, self.probabilities, self.correct_prediction],
            feed_dict=feed_dict)
        return acc, pred, probabilities, tags