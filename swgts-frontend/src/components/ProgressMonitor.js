import React from 'react';

import { LinearProgress} from '@mui/material';


class ProgressMonitor extends React.Component {

    render() {
    return (
        <React.Fragment>
        <LinearProgress variant="buffer" value={this.props.filtered/Math.max(this.props.total,1)*100} sx = {{height:"10px"}} valueBuffer={this.props.progress/Math.max(this.props.total,1)*100} />
        {this.props.progress}/{this.props.total} transferred ({this.props.filtered} filtered)
        <LinearProgress variant="determinate" value={this.props.buffer_fill/Math.max(this.props.buffer_size,1)*100} sx = {{height:"10px"}} color="secondary"/>
        {this.props.buffer_fill}/{this.props.buffer_size} bytes in buffer
        </React.Fragment>
        );
    }
}




export {ProgressMonitor};
