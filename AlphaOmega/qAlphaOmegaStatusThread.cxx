#include "qAlphaOmegaStatusThread.h"

// STD Includes
#include <cmath> // NAN
// #include <stdlib.h> 

// Windows
#include <Windows.h>

// AlphaOmega SDK
#include "AOSystemAPI.h"
#include "AOTypes.h"
#include "StreamFormat.h"

#include "vtkMRMLScriptedModuleNode.h"

static const float DRIVE_ZERO_POSITION_MILIM = 25.0;
static const int SLEEP_TIME_MILIS = 500;


vtkMRMLScriptedModuleNode* qAlphaOmegaStatusThread::param;

qAlphaOmegaStatusThread::qAlphaOmegaStatusThread(QObject *parent)
    : QThread(parent)
{

}

qAlphaOmegaStatusThread::~qAlphaOmegaStatusThread()
{
  this->Mutex.lock();
  this->Abort = true;
  this->Condition.wakeOne();
  this->Mutex.unlock();
  wait();
}


float qAlphaOmegaStatusThread::GetDistanceToTargetMiliM()
{
	int32 nDepthUm = 0;
	EAOResult eAORes = (EAOResult)GetDriveDepth(&nDepthUm);

	if (eAORes == eAO_OK)
	{
    return DRIVE_ZERO_POSITION_MILIM - nDepthUm / 1000.0;
  }
  else
  {
    return NAN;
  }
}


void qAlphaOmegaStatusThread::run()
{

  bool deviceWasConnected = false;
  bool deviceIsConnected = false;

  float previousDistanceToTargetMiliM = NAN;
  float distanceToTargetMiliM = NAN;

  float dtts[] = {9.499,9.499,9.499,9.499,9.499,9.499,9.499,9.499,9.499,9.499,7.491,6.990,6.487,5.986,5.483,4.980,4.479,3.977,3.475,2.974,2.473,1.970,1.468,0.967,0.467,0.466,-0.027,-0.035,-0.538,-1.039,-1.541,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033,-3.033};
  unsigned int dtt_index = 0;

  forever
  {

    Sleep(SLEEP_TIME_MILIS);

    this->Mutex.lock();

    // deviceIsConnected = (isConnected() == eAO_CONNECTED);
    // if (deviceIsConnected != deviceWasConnected)
    // {
    //   emit connectionStatusModified(&deviceIsConnected);
    //   deviceWasConnected = deviceIsConnected;
    // }

    distanceToTargetMiliM = std::stof(this->param->GetParameter("dtt"));
    // distanceToTargetMiliM = this->GetDistanceToTargetMiliM();
    // distanceToTargetMiliM = 10.0 * ((float) rand()) / (float) RAND_MAX;
    if (distanceToTargetMiliM != previousDistanceToTargetMiliM)
    {
      emit distanceToTargetModified(&distanceToTargetMiliM);
      previousDistanceToTargetMiliM = distanceToTargetMiliM;
    }

    this->Mutex.unlock();

  }
}
