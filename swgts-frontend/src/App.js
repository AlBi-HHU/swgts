import './App.css';
import axios from 'axios';

import React, { Component } from 'react';

import {LoadDataView} from './components/LoadDataView.js';
import {uploadFASTQ} from './data/FASTQProcessing.js';
import {ProgressMonitor} from './components/ProgressMonitor.js';
import {InfoDialog} from './components/InfoDialog.js';
import GitInfo from 'react-git-info/macro';

//GIT
const gitInfo = GitInfo();

//axios.defaults.baseURL = 'https://localhost/'

class App extends Component{

  constructor(props) {
    super(props);
    this.state = {
      text: 'App.js',
      dialogVisible: false,
        uploading:false,
      dialogText : '?',
      serverVersionText : '?',
        buffer_size : null,
        progress : 0,
        total : 0,
        buffer_fill : 0,
        filtered : 0,
    }

    //Binds (to access THIS later)
    this.dialogCallback = this.dialogCallback.bind(this);
    this.closeDialog = this.closeDialog.bind(this);
    this.initiate_upload = this.initiate_upload.bind(this);


  }
  //Lifecycle Methods
  componentDidMount() {
      //TODO: Fetch backend version and display, verify compatibility
      axios.get('/api/server-status').then(
          (response) => {
              this.updateServerStatus(response);
              this.setState({buffer_size: response.data['maximum pending bytes']});
          }
      ).catch((error) => {console.log('Unable to connect to backend')})

      this.updateServerStatus = this.updateServerStatus.bind(this);
        this.updateProgress = this.updateProgress.bind(this);
        this.updateTotal = this.updateTotal.bind(this);
        this.updateBufferFill = this.updateBufferFill.bind(this);
        this.updateFiltered = this.updateFiltered.bind(this);
        this.initiate_upload = this.initiate_upload.bind(this);
  }
  
  /***           CALLBACKS         ***/
  
  updateServerStatus(response){
        this.setState(
            {serverVersionText : response.data.commit + ':' + response.data.date + ' Uptime: '+Math.round(response.data.uptime*100)/100+'s'}
        );  
  }
  
  //Does two things: a) sets the info dialog to visible and b) changes the text
  dialogCallback(newText){
    this.setState(
        {
            dialogVisible : true,
            dialogText : newText
        }
    )
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
  closeDialog(){
    this.setState({dialogVisible : false})
  }

initiate_upload(file_list, download){
      this.setState({'uploading':true, 'filtered': 0, 'progress' : 0})
      uploadFASTQ(
            file_list, download, this.updateProgress, this.updateTotal, this.updateBufferFill,this.updateFiltered, this.dialogCallback
      ).then(
          () => this.setState({'uploading' : false})
      )


}
  
  //Main render function
  render() {
  return(
    <div className="App">
      <small>{ 'SWGTS Demo, Version: ' + gitInfo.commit.date }</small>
      <br/>
      <small>Last commit: {gitInfo.commit.message}</small>
      <br/>
      <small>Server Version: {this.state.serverVersionText}</small>
      {this.state.uploading ? null : <LoadDataView className = "ldv" dialogCallback = {this.dialogCallback} initiate_upload = {this.initiate_upload}> </LoadDataView>}
       {this.state.uploading ? <ProgressMonitor
           dialogCallback = {this.dialogCallback} buffer_size = {this.state.buffer_size}
           total = {this.state.total}
           progress = {this.state.progress}
           filtered = {this.state.filtered}
           buffer_fill = {this.state.buffer_fill}
       /> : null }
      {this.state.dialogVisible ? <InfoDialog text={this.state.dialogText} closeInfoDialog={this.closeDialog}/> : null}
    </div>
    );
  }
}

export default App;
