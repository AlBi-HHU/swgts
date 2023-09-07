import React from 'react';

import {FormControlLabel, Switch, Button, Box} from '@mui/material';

//can obviously be spoofed/faked, final check should consider MIMEtypes
const ALLOWED_EXTENSIONS = ['.fastq.gz','.fq.gz','.fastq','.fq']

class LoadDataView extends React.Component {

    constructor(props){
        super(props);
        this.state={
        'download_files' : false, //TODO: Could be separated from this component and be managed elsewhere
        'input_files': []
        };



        this.update_file_list = this.update_file_list.bind(this);
        this.drop = this.drop.bind(this);
        this.click = this.click.bind(this);
    }


    updateProgress(progress){
        this.setState(
        {'progress' : this.state.progress + progress}
        );
    }
    
    updateTotal(total){
        this.setState(
        {'total' : total}
        );
    }
    updateBufferFill(total){
        this.setState(
        {'buffer_fill' : total}
        );
    }
    updateFiltered(total){
        this.setState(
        {'filtered' : total}
        );
    }

    update_file_list(files){
      if ([...files].every(file => ALLOWED_EXTENSIONS.some(extension => file.name.endsWith(extension))) && files.length <= 2){
          this.setState({"input_files":[...files]})
        return true;
      }
      else{
          //reject
        this.props.dialogCallback('Only one or two files can be uploaded, allowed extensions are: '+ALLOWED_EXTENSIONS.join(', '));
        return false;
      }
    }

    dragenter(event){
        event.preventDefault()
        event.stopPropagation()
        event.currentTarget.classList.add('highlight')
    }
    dragover(event){
        event.preventDefault()
        event.stopPropagation()
        event.currentTarget.classList.add('highlight')
    }
    dragleave(event){
        event.preventDefault()
        event.stopPropagation()
        event.currentTarget.classList.remove('highlight')
    }
    drop(event){
        event.preventDefault()
        event.stopPropagation()
        event.currentTarget.classList.remove('highlight')
      if (event.dataTransfer.files !== null){
        this.update_file_list(event.dataTransfer.files)
      }
    }

    click(event){
        if (this.update_file_list(event.target.files) === false ){
            event.target.value = '';
        }
    }
    render() {

    return (
        <React.Fragment>

            <div id="drop-area" onDragEnter={this.dragenter} onDragOver={this.dragover} onDragLeave={this.dragleave} onDrop={this.drop}>
          <form className="drop-form">
            <p>Drag and drop files</p>
        <input
            id="fileElem"
        type="file"
        multiple //Allow multiple files for paired sequencing
        onChange={this.click}
        accept={ALLOWED_EXTENSIONS.join(',')}
        />
              <label className="upload-button" htmlFor="fileElem">Select files</label>
          </form>
        </div>

            {(this.state.input_files.length !== 0) ? "Selected Files: " + this.state.input_files.map(x=>x.name).join('\t') : null}

        <Box className = "loadDataView" style={this.state.disabled ? {pointerEvents: "none", opacity: "0.4"} : {}}>



            <Button
                id={"upload_button"}
                variant="contained"
                onClick={() =>
                {

                    //Check for mode
                    if (this.state.input_files.length === 0){
                        this.props.dialogCallback(`Please select a file for uplading!`);
                        return;
                    }

                    this.props.initiate_upload(Array.from(this.state.input_files),this.state.download_files)
                }
                }
            >
            Upload FASTQ
            </Button>

            <FormControlLabel control={
                <Switch onChange={(e,checked) => this.setState({'download_files' : checked})
                }/>} label="Download filtered files"/>
          </Box>
                </React.Fragment>
        );
    }
}




export {LoadDataView};
