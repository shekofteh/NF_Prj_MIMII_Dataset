print('load feature_extractore_pre_nnFilterDenoise')


class feature_extractor_pre_nnFilterDenoise(feature_extractor):
    def __init__(self, base_folder, name='welch'):
        super().__init__(base_folder,name,
                        xlabel = 'time',
                        ylabel = 'amp',
                        zlabel = 'none')
        
        self.stack = False
        # set type
        self.para_dict['type'] = feature_extractor_type.preNNFILTER
        self.para_dict['type_name'] = 'preNNfilter'
        # default hyper
        self.set_hyperparamter()


    def set_hyperparamter(self,
                           aggregation=np.average,
                           nfft=2048, 
                           channel = 'all'):

        self.para_dict['hyperpara']={ \
                'aggregation': aggregation,
                'nfft': nfft}
        
        self.para_dict['file_name_mainhyperparastr'] = 'nf'+str(nfft)

        if os.path.isfile(self._full_wave_path()):
                self.create_from_wav(self.para_dict['wave_filepath'] )
        
    def create_from_wav(self, filepath):
        
        # assuming for now all channels
        self.para_dict['data_channel_use_str'] = 'ch'+'All'
        af = np.array(self._read_wav(filepath))
        
        for c in range(af.shape[0]):
            # Stft
            S = np.abs(librosa.stft(af[c,:],n_fft=self.para_dict['hyperpara']['nfft']))
            nlm = librosa.decompose.nn_filter(S,aggregate=self.para_dict['hyperpara']['aggregation'])
            den = librosa.core.istft(nlm)
            af[c,:len(den)] = librosa.core.istft(nlm)
            af[c,len(den):]=0.

            
        self.feature_data = af
    
    def get_wav_memory_file(self):
        wmf = feature_extractor_memory_wave_file()
        wmf.filepath = self.para_dict['wave_filepath']
        wmf.channel = self.feature_data
        wmf.srate= self.para_dict['wave_srate']
        wmf.length = self.feature_data.shape[1]
        return wmf