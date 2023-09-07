import React from 'react';

import {Button} from '@mui/material';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';

class InfoDialog extends React.Component {
     //TODO: Localization applied to strings
    
    render() {

    return (
          <Dialog
            open={true}
            onClose={this.handleClose}
            aria-labelledby="alert-dialog-title"
            aria-describedby="alert-dialog-description"
          >
            <DialogTitle id="alert-dialog-title">{"Info"}</DialogTitle>
            <DialogContent>
              <DialogContentText id="alert-dialog-description">
                {this.props.text}
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={this.props.closeInfoDialog} color="primary">
                OK
              </Button>
            </DialogActions>
          </Dialog>  
        );
    }
}




export {InfoDialog};
