if __name__ == '__main__':
    from traits.etsconfig.api import ETSConfig
    ETSConfig.toolkit = 'qt4'

    import os
    os.environ['TRAITS_DEBUG'] = "1"

from traits.api import HasTraits, List
from traitsui.api import View, Item

from cytoflowgui.vertical_notebook_editor import VerticalNotebookEditor
from cytoflowgui.workflow_item import WorkflowItem



class Workflow(HasTraits):
    """
    A list of WorkflowItems.
    """

    workflow = List(WorkflowItem)
    
    traits_view = View(Item(name='workflow',
                            id='table',
                            editor=VerticalNotebookEditor(page_name='.name',
                                                          page_description='.id',
                                                          view = 'traits_view',
                                                          scrollable = True,
                                                          multiple_open = False),
                            show_label = False
                            ),
                       #resizable = True
                       )