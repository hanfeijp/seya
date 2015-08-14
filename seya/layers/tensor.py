import theano.tensor as T

from theano import scan

from keras.layers.recurrent import Recurrent
from keras import initializations, regularizers, constraints

from ..utils import apply_model


class Tensor(Recurrent):
    '''Tensor class
    Motivated by the Fast Approximate DPCN model

    Parameters:
    ===========
    *_dim defines the dimensions of the tensorial transition
    hid2output: is a sequential model to transform the hidden states
        to the output causes.
    '''
    def __init__(self, input_dim, output_dim, causes_dim,
                 hid2output,
                 init='glorot_uniform',
                 W_regularizer=None,
                 W_constraint=None,
                 b_regularizer=None,
                 b_constraint=None,
                 activity_regularizer=None,
                 truncate_gradient=-1,
                 weights=None, name=None,
                 return_mode='both',
                 return_sequences=True):
        super(Tensor, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.causes_dim = causes_dim
        self.hid2output = hid2output
        self.init = initializations.get(init)
        self.truncate_gradient = truncate_gradient
        self.input = T.tensor3()
        self.return_mode = return_mode

        self.W = self.init((input_dim, causes_dim, output_dim))
        self.C = self.init((output_dim, output_dim))

        self.params = [self.W, self.C] + hid2output.params

        self.regularizers = []
        self.W_regularizer = regularizers.get(W_regularizer)
        if self.W_regularizer:
            self.W_regularizer.set_param(self.W)
            self.regularizers.append(self.W_regularizer)

        self.b_regularizer = regularizers.get(b_regularizer)
        if self.b_regularizer:
            self.b_regularizer.set_param(self.b)
            self.regularizers.append(self.b_regularizer)

        self.activity_regularizer = regularizers.get(activity_regularizer)
        if self.activity_regularizer:
            self.activity_regularizer.set_layer(self)
            self.regularizers.append(self.activity_regularizer)

        self.W_constraint = constraints.get(W_constraint)
        self.b_constraint = constraints.get(b_constraint)
        self.constraints = [self.W_constraint, self.b_constraint]

        if weights is not None:
            self.set_weights(weights)

        if name is not None:
            self.set_name(name)

    def set_name(self, name):
        self.W.name = '%s_W' % name
        self.C.name = '%s_C' % name

    def _step(self, Wx_t, s_tm1, u_tm1):
        uWx = (u_tm1[:, :, None] * Wx_t).sum(axis=1)  # shape: batch x output_dim
        s_t = uWx + T.dot(s_tm1, self.C)
        u_t = apply_model(self.hid2output, s_t)
        return s_t, u_t

    def get_output(self, trian=False):
        X = self.get_input()
        Wx = T.tensordot(X, self.W, axes=(2, 0)).dimshuffle(1, 0, 2, 3)
        s_init = T.zeros((X.shape[0], self.output_dim))
        u_init = T.zeros((X.shape[0], self.causes_dim))
        outputs, uptdates = scan(
            self._step,
            sequences=[Wx],
            outputs_info=[s_init, u_init],
            truncate_gradient=self.truncate_gradient)

        if self.return_mode == 'both':
            return T.concatenate([outputs[0], outputs[1]],
                                 axis=-1).dimshuffle(1, 0, 2)
        elif self.return_mode == 'states':
            return outputs[0].dimshuffle(1, 0, 2)
        elif self.return_mode == 'causes':
            return outputs[1].dimshuffle(1, 0, 2)
        else:
            raise ValueError("return_model {0} not valid. Choose "
                             "'both', 'states' or 'causes'".format(self.return_mode))
