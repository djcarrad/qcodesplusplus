from PyQt5 import QtWidgets
import numpy as np
import os
import json
from qcodesplusplus.data.data_set import load_data
import qcodesplusplus.plotting.offline.main as main


class qcodesppData(main.BaseClassData):

    def __init__(self, filepath, canvas, metapath, load_the_data=True):
        super().__init__(filepath, canvas)
        # Open meta file and set label
        self.filepath = filepath
        with open(metapath) as f:
            self.meta = json.load(f)
        dirname = os.path.basename(os.path.dirname(metapath))
        # timestamp = self.meta['timestamp'].split(' ')[1]

        self.label = f'{dirname.split('#')[1]}'
        # self.raw_data = None
        

        self.independent_parameters = []
        self.independent_parameter_names = []
        self.dependent_parameters = []
        self.dependent_parameter_names = []
        self.all_parameters = []
        self.all_parameter_names = []
        
        
        
        self.channels = self.meta['arrays']

        if load_the_data:
            if '.dat' in filepath:
                self.dataset=load_data(os.path.dirname(filepath))
            else:
                self.dataset=load_data(filepath)

            self.identify_independent_vars()

            self.prepare_dataset()

            self.data_loaded=True
        
        else:
            self.data_loaded=False
            self.dataset=None

        self.index_x = 0
        self.index_y = 1

        #self.dataset_id = "#" + self.dataset.location.split("#", 1)[1].split("_", 1)[0]
        self.dataset_id = "#" + dirname.split("#", 1)[1].split("_", 1)[0]
        self.settings["title"] = self.dataset_id
        self.DEFAULT_PLOT_SETTINGS['title']= self.dataset_id
    


    def prepare_dataset(self):
        
        self.data_dict = self.dataset.arrays
        pars = list(self.data_dict.keys())
        self.dims = self.data_dict[pars[1]].shape


        if len(self.independent_parameters) > 1:
            pars = list(self.data_dict.keys())
            self.dims = self.data_dict[pars[1]].shape
            if len(self.data_dict[self.all_parameters[0]["array_id"]]) < self.dims[0]*self.dims[1]:
                self.data_dict[self.all_parameters[0]["array_id"]] = np.repeat(self.data_dict[self.all_parameters[0]["array_id"]], self.dims[1])


    def isFinished(self):
        set_x = self.data_dict[self.all_parameters[0]["array_id"]]
        set_x = np.unique(set_x[~np.isnan(set_x)])
        return len(set_x) == self.dims[0]
    

    def finished_dimensions(self):
        set_x = self.data_dict[self.all_parameters[0]["array_id"]]
        set_x = np.unique(set_x[~np.isnan(set_x)])
        self.dims = [len(set_x)-1, self.dims[1]]
    

    
    def get_column_data(self):
        self.prepare_dataset()
        # If user has selected X data, use that, otherwise use the first independent parameter
        # X data is the same no matter the data dimension
        if self.settings['X data'] != '':
            xdata = self.data_dict[self.settings['X data']]
            self.settings['xlabel'] = f'{self.channels[self.settings['X data']]['label']} ({self.channels[self.settings['X data']]['unit']})'
        else:
            xdata = self.data_dict[self.all_parameters[self.index_x]["array_id"]]
            self.settings["xlabel"] = "{} ({})".format(self.independent_parameters[0]["label"], self.independent_parameters[0]["unit"])
        
        if len(self.independent_parameters) == 1: # data is 1D
            if self.settings['Y data'] != '':
                ydata = self.data_dict[self.settings['Y data']]
                self.settings['ylabel'] = f'{self.channels[self.settings['Y data']]['label']} ({self.channels[self.settings['Y data']]['unit']})'
            else:
                ydata = self.data_dict[self.dependent_parameters[self.index_dependent_parameter]["array_id"]]
                self.settings["xlabel"] = "{} ({})".format(self.independent_parameters[0]["label"], self.independent_parameters[0]["unit"])
            column_data = np.column_stack((xdata, ydata))

        elif len(self.independent_parameters) > 1: # data is 2D
            # In this case it's possible to select a 2D array as the X data, but X data MUST always be 1D
            # In future, I will add that each X point is the average of that row in the 2D array

            if self.settings['Y data'] != '':
                ydata = self.data_dict[self.settings['Y data']]
                self.settings['ylabel'] = f'{self.channels[self.settings['Y data']]['label']} ({self.channels[self.settings['Y data']]['unit']})'
            else:
                ydata = self.data_dict[self.all_parameters[self.index_y]["array_id"]]
                self.settings["ylabel"] = "{} ({})".format(self.all_parameters[self.index_y]["label"], self.independent_parameters[1]["unit"])

            if self.settings['Z data'] != '':
                zdata = self.data_dict[self.settings['Z data']]
                self.settings['clabel'] = f'{self.channels[self.settings['Z data']]['label']} ({self.channels[self.settings['Z data']]['unit']})'
            else:
                zdata = self.data_dict[self.dependent_parameters[self.index_dependent_parameter]["array_id"]]
                self.settings["clabel"] = "{} ({})".format(self.dependent_parameters[self.index_dependent_parameter]["label"], self.dependent_parameters[self.index_dependent_parameter]["unit"])
            
            column_data = np.column_stack((xdata.flatten(),
                                         ydata.flatten(),
                                        zdata.flatten()
                                        ))

            # # Delete unfinished rows to enable plotting
            if not self.isFinished():
                self.finished_dimensions()

                column_data = column_data[~np.isnan(column_data).any(axis=1)]
                column_data = column_data[~np.isnan(column_data[:,0])]
                column_data = column_data[:self.dims[0]*self.dims[1]]

        else:
            return np.empty((1,1))
          
        self.measured_data_points = column_data.shape[0]

        return column_data
    

    def load_and_reshape_data(self, reload_data=False,reload_from_file=True):
        if not self.data_loaded or reload_data and reload_from_file:
            if '.dat' in self.filepath:
                self.dataset=load_data(os.path.dirname(self.filepath))
            else:
                self.dataset=load_data(self.filepath)

            self.identify_independent_vars()

            self.prepare_dataset()

            self.data_loaded=True

        column_data = self.get_column_data()
        if column_data.ndim == 1: # if empty array or single-row array
            self.raw_data = None
        else:
            # # Determine the number of unique values in the first column to determine the shape of the data
            columns = self.get_columns()
            data_shape = self.dims

            if data_shape[0] > 1: # If two or more sweeps are finished
                
                # Determine if file is 1D or 2D by checking if first two values in first column are repeated
                if len(data_shape) == 1:
                    self.raw_data = [column_data[:,x] for x in range(column_data.shape[1])]            
                    columns = columns[:2]
                else: 
                    # flip if first column is sorted from high to low 
                    if column_data[:,columns[0]][-1] < column_data[:,columns[0]][0]: 
                        column_data = np.flipud(column_data)
                        self.udflipped=True
                    self.raw_data = [np.reshape(column_data[:,x], data_shape) 
                                     for x in range(column_data.shape[1])]
                    # flip if second column is sorted from high to low
                    if self.raw_data[1][0,0] > self.raw_data[1][0,1]: 
                        self.raw_data = [np.fliplr(self.raw_data[x]) for x in range(column_data.shape[1])]
                        self.lrflipped=True
                        
            elif data_shape[0] == 1: # if first two sweeps are not finished -> duplicate data of first sweep to enable 3D plotting
                self.raw_data = [np.tile(column_data[:data_shape[1],x], (2,1)) for x in range(column_data.shape[1])]    
                # if len(unique_values) > 1: # if first sweep is finished -> set second x-column to second x-value
                #     self.raw_data[columns[0]][0,:] = unique_values[0]
                #     self.raw_data[columns[0]][1,:] = unique_values[1]
                # else: # if first sweep is not finished -> set duplicate x-columns to +1 and -1 of actual value
                self.raw_data[columns[0]][0,:] = columns[0]-1
                self.raw_data[columns[0]][1,:] = columns[0]+1
            else:
                self.raw_data = None
                
            self.settings['columns'] = ','.join([str(i) for i in columns])
    


    def identify_independent_vars(self):        
        for chan in self.channels.keys():
            if self.channels[chan]["array_id"] not in self.all_parameter_names:
                if self.channels[chan]["is_setpoint"] and self.channels[chan]["array_id"] in list(self.dataset.arrays.keys()):
                    self.independent_parameters.append(self.channels[chan])
                    self.independent_parameter_names.append(self.channels[chan]["array_id"])
                elif self.channels[chan]["array_id"] in list(self.dataset.arrays.keys()):
                    self.dependent_parameters.append(self.channels[chan])
                    self.dependent_parameter_names.append(self.channels[chan]["array_id"])
        self.all_parameters = self.independent_parameters + self.dependent_parameters
        self.all_parameter_names = self.independent_parameter_names + self.dependent_parameter_names
        
        # Default to conductance as dependent variable if present.
        defnamefound=False
        for paramname in ['onductance','esistance', 'urr', 'olt']:
            for name in self.dependent_parameter_names:
                if not defnamefound:
                    if paramname in name:
                        self.index_dependent_parameter = self.dependent_parameter_names.index(name)
                        defnamefound=True
        if not defnamefound: 
            self.index_dependent_parameter = 0

        self.settings['X data'] = self.independent_parameter_names[0]

        if len(self.independent_parameters) > 1:
            self.settings['Y data'] = self.independent_parameter_names[1]
            self.settings['Z data'] = self.dependent_parameter_names[self.index_dependent_parameter]

        else:
            self.settings['Y data'] = self.dependent_parameter_names[self.index_dependent_parameter]

            self.settings.pop('Z data', None)

        self.settings_menu_options = {'X data': self.all_parameter_names,
                                      'Y data': self.all_parameter_names,
                                      'Z data': self.all_parameter_names}
        
        self.filter_menu_options = {'Multiply': self.all_parameter_names,
                                    'Divide': self.all_parameter_names,
                                    'Offset': self.all_parameter_names}
        
    # Redefine apply_all_filters so that data from other columns can be sent to the filters.
    def apply_all_filters(self, update_color_limits=True):
        for filt in self.filters:
            if filt.checkstate:
                if filt.name in ['Multiply', 'Divide', 'Offset']:
                    if filt.settings[0][0]=='-':
                        arrayname=filt.settings[0][1:]
                        setting2='-'
                    else:
                        arrayname=filt.settings[0]
                        setting2='+'
                    if arrayname in self.all_parameter_names:
                        if len(self.independent_parameters) > 1:
                            array=self.data_dict[arrayname][:self.dims[0]][:self.dims[1]]
                        else:
                            array=self.data_dict[arrayname][:self.dims[0]]
                        if hasattr(self,'udflipped'): # If the calculated column data got flipped.
                            array=np.flipud(array)
                        if hasattr(self,'lrflipped'):
                            array=np.fliplr(array)
                    else:
                        array=None
                    
                    self.processed_data = filt.function(self.processed_data, 
                                                filt.method,
                                                filt.settings[0], 
                                                setting2,
                                                array)
                else:
                    self.processed_data = filt.function(self.processed_data, 
                                                    filt.method,
                                                    filt.settings[0], 
                                                    filt.settings[1])
        if update_color_limits:
            self.reset_view_settings()
            if hasattr(self, 'image'):
                self.apply_view_settings()

# Old way of choosing axes. Basically is broken now but could be reintroduced
    # def add_extension_actions(self, editor, menu):
    #     channel_menu = menu.addMenu('Select X...')
    #     for par in self.all_parameter_names:
    #         par_name = par
    #         action = QtWidgets.QAction(par_name, editor)
    #         action.setData("x")
    #         channel_menu.addAction(action) 

    #     channel_menu = menu.addMenu('Select Y...')
    #     for par in self.all_parameter_names:
    #         par_name = par
    #         action = QtWidgets.QAction(par_name, editor)
    #         action.setData("y")
    #         channel_menu.addAction(action) 
    #     if len(self.independent_parameters) > 1:
    #         channel_menu = menu.addMenu('Select Z...')
    #         for par in self.all_parameter_names:
    #             par_name = par
    #             action = QtWidgets.QAction(par_name, editor)
    #             action.setData("z")
    #             channel_menu.addAction(action)
    #     menu.addSeparator()




    # def do_extension_actions(self, editor, signal):
    #     if signal.text() in self.all_parameter_names and signal.data() == "z":
    #         self.index_dependent_parameter = self.dependent_parameter_names.index(signal.text())
    #         self.load_and_reshape_data()
    #         editor.update_plots()
    #         editor.show_current_all()
    #     if signal.text() in self.all_parameter_names and signal.data() == "y":
    #         if len(self.independent_parameters) == 1:
    #             self.index_dependent_parameter = self.dependent_parameter_names.index(signal.text())
    #         else:
    #             self.index_y = self.all_parameter_names.index(signal.text())
    #         self.load_and_reshape_data()
    #         editor.update_plots()
    #         editor.show_current_all()
    #     if signal.text() in self.all_parameter_names and signal.data() == "x":
    #         self.index_x = self.all_parameter_names.index(signal.text())
    #         self.load_and_reshape_data()
    #         editor.update_plots()
    #         editor.show_current_all()