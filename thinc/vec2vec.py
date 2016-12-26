from .base import Model


class Affine(Model):
    name = 'affine'

    def setup(self, components, **kwargs):
        if isinstance(components[0], int):
            self.W = self.ops.allocate(components, name=(self.name, 'W'))
            self.b = self.ops.allocate((components[0],), name=(self.name, 'b'))
        else:
            self.W, self.b = components

    @property
    def shape(self):
        return self.W.shape

    @property
    def nr_out(self):
        return self.shape[0]

    @property
    def nr_in(self):
        return self.shape[1]

    def predict_batch(self, input_BI):
        return self.ops.affine(input_BI, self.W, self.b)

    def begin_update(self, input_BI, drop=0.0):
        output_BO = self.ops.affine(input_BI, self.W, self.b)
        mask = self.ops.get_dropout(output_BO.shape, drop)
        if mask is not None:
            output_BO *= mask
        return output_BO, self._get_finish_update(input_BI, mask)
    
    def _get_finish_update(self, acts_BI, mask):
        def finish_update(d_acts_BO, sgd, **kwargs):
            d_acts_BO *= mask
            self.d_b += d_acts_BO.sum(axis=0)
            outer = self.ops.batch_outer(d_acts_BO, acts_BI)
            self.d_W += outer
            d_acts_BI = self.ops.batch_dot(d_acts_BO, self.W.T)
            return d_acts_BI
        return finish_update


class ReLu(Affine):
    name = 'affine'
    def predict_batch(self, input_BI):
        output_BO = self.ops.affine(input_BI, self.W, self.b)
        return self.ops.clip_low(output_BO, 0, inplace=True)

    def begin_update(self, input_BI, drop=0.0):
        output_BO = self.ops.affine(input_BI, self.W, self.b)
        mask = self.ops.get_dropout(output_BO.shape, drop)
        mask *= output_BO > 0
        output_BO *= mask
        return output_BO, self._get_finish_update(input_BI, mask)


class Maxout(Affine):
    name = 'maxout'    
    def predict_batch(self, input_bi):
        take_which = self.ops.take_which
        argmax = self.ops.argmax
        affine = self.ops.affine
        return take_which(argmax(affine(input_bi, self.W, self.b)))

    def begin_update(self, input_BI, drop=0.0):
        W_OCI = self.W
        b_OC = self.b
        output_BOC = self.ops.affine(input_BI, W_OCI, b_OC)
        which_BO = self.ops.argmax(output_BOC, axis=-1)
        best_BO = self.ops.take_which(output_BOC, which_BO)
        mask_BO = self.ops.get_dropout(best_BO.shape, drop)
        finish_update = self._get_finish_update(input_BI, which_BO, mask_BO)
        best_BO *= mask_BO
        return best_BO, finish_update

    def _get_finish_update(self, acts_BI, which_BO, mask_BO):
        def finish_update(d_acts_BO):
            raise NotImplementedError
            #d_acts_BO *= mask_BO
            ## TODO
            #self.d_b += d_acts_BO.sum(axis=0)
            #self.d_W += d_W_OCI
            #return d_acts_BI
        return backward