// simple simulation for neocortix cloud services
//package neocortix

import scala.concurrent.duration._
import scala.io.Source

import io.gatling.core.Predef._
import io.gatling.http.Predef._

class simpleSim_RampLong extends Simulation {
  val httpProtocol = http
    .baseUrl("https://loadtest-target.neocortix.com")
    .acceptHeader("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8") // 6
    .doNotTrackHeader("1")
    .acceptLanguageHeader("en-US,en;q=0.5")
    .acceptEncodingHeader("gzip, deflate")
    .userAgentHeader("Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0")
    .shareConnections

  val scn = scenario("scenario_1")
    .exec(http("request_1")
      .get("/"))
    .pause( 100.milliseconds )
    .exec(http("request_2")
      .get("/"))
    .pause( 1000.milliseconds )
    .exec(http("request_3")
      .get("/"))
    .pause( 1000.milliseconds )
    /**
    .exec(http("request_4")
      .get("/"))
    .pause( 1000.milliseconds )
    .exec(http("request_5")
      .get("/"))
    .pause( 1000.milliseconds )
    */

  val userMultiple = 2;

  setUp(
    scn.inject(
      incrementConcurrentUsers( userMultiple )
        .times(5)
        .eachLevelLasting(50.seconds)
        .separatedByRampsLasting(10.seconds)
        .startingFrom(0),
      constantConcurrentUsers( 5 * userMultiple ) during (210 seconds )
      )
  ).protocols(httpProtocol)
}