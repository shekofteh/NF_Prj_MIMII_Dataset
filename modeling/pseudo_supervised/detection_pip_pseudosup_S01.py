print('Load detection_pipe')

# main imports
import numpy as np
import pickle
import os
from datetime import datetime

## PipeThreading objects
from queue import Queue
from threading import Thread

class Pipe(object):
    def __init__(self, preprocessing_steps=None, modeling_step=None, pseudo_sup=False):        
        # instantiate evaluating parameters
        self.roc_auc = None

        # instantiate the preprocessing steps
        self.preproc_steps = [step(**kwargs) for step, kwargs in preprocessing_steps]        

        # create the predictive model             
        self._mdl, self.model_args = modeling_step # model object
        # model instance
        self.model = self._mdl(**self.model_args)
        
        # toggle flag for pseudo supervised to have classes >0 -> 0 1 and not -1 and 1
        self.pseudo_sup = pseudo_sup

    def to_pickle(self, filepath=None):
        self.update_filepath(filepath)

        with open(self.filepath, 'wb') as f:
            pickle.dump(self, f)

    def update_filepath(self, path=None):
        if not os.path.exists('pipes'):
            os.mkdir('pipes')
        
        if not path or (type(path)==dict):
            if not path:
                task = self.task
            else:
                task = path
                self.filepath = './pipes/' + '_'.join([ task['feat_col'],
                                    ''.join([str(i) for i in list(task['feat'].values())]),
                                    task['SNR'],
                                    task['machine'],
                                    'ID'+task['ID'],
                                    self.model.name,
                                    self.model.sufix,
                                    datetime.now().strftime("%Y%m%d_%H%M%S")
                                    ]) + '.pkl'
        else:
            self.filepath = path


    def get_data(self, task):
        self.df_train, data_train = load_data(train_set=1, **task)
        self.df_test, data_test = load_data(train_set=0, **task)
        if self.pseudo_sup:
            self.ground_truth = self.df_test.abnormal
        else:
            self.ground_truth = self.df_test.abnormal.replace(to_replace=1, value=-1).replace(to_replace=0, value=1)
        # update filepath accordingly to task
        self.update_filepath(task)

        return data_train, data_test

    def preprocess(self, data_train, data_test):
        # run through all the preprocessing steps
        for step in self.preproc_steps:
            data_train =  step.fit_transform(data_train)
            data_test = step.transform(data_test)

        # return preprocessed data
        return data_train, data_test
    
    def preprocess_post(self, data_train, data_test):
        # run through all the preprocessing steps
        for step in self.preproc_steps:
            data_train =  step.transform(data_train)
            data_test = step.transform(data_test)

        # return preprocessed data
        return data_train, data_test

    def fit_model(self, data_train):
        # get ground truth for train_set
        if self.pseudo_sup:
            self.y_train = self.df_train.abnormal.replace(to_replace=-1, value=1)
        else:
            self.y_train=None
        # fit the model
        self.model.fit(data_train, y=self.y_train)
        
        if self.pseudo_sup: print(self.model.eval_roc_auc(data_train, self.y_train))

    def evaluate(self, data_test, ground_truth):
        # calculate evaluation score

        self.df_test['pred_scores'] = self.model.predict_score(data_test)
        self.df_test['pred_labels'] = self.model.predict(data_test)
        self.roc_auc = self.model.eval_roc_auc(data_test, ground_truth)

    def run_pipe(self, task):
        self.task = task
        # get the data
        print('...loading data')
        data_train, data_test = self.get_data(task)
        print('data loading completed\n\n...preprocessing data')

        # preprocessing
        data_train, data_test = self.preprocess(data_train, data_test)
        print('data preprocessing finished\n\n...fitting the model')

        # fitting the model
        self.fit_model(data_train)
        print('model fitted successfully\n\n...evaluating model')

        # evaluating over ground truth
        self.evaluate(data_test, self.ground_truth)
        print('evaluation successfull, roc_auc:', self.roc_auc)

        # saving to pickle
        self.to_pickle()
        print('pipe saved to pickle')
        return True
    

# thread class
class PipeThread(Thread):

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue
        self.stop = False

    def run(self):
        while not self.stop:
            # Get the work from the queue and expand the tuple
            pipe, task = self.queue.get()  
            # run the pipe
            pipe.run_pipe(task)
            # return done
            self.queue.task_done()